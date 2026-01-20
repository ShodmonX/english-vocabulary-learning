from __future__ import annotations

from datetime import timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.bot.keyboards.profile import profile_back_kb, profile_refresh_kb, stars_packages_kb
from app.bot.keyboards.credits import credits_topup_methods_kb
from app.config import settings
from sqlalchemy import select

from app.db.models import StarsPayment
from app.db.repo.credits import get_profile_summary
from app.db.repo.app_settings import get_admin_contact_username
from app.db.repo.packages import get_active_package, list_packages
from app.db.repo.stars_payments import create_pending_payment, credit_paid_payment, mark_failed
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.services.i18n import b, t

router = Router()


def _format_refill(dt) -> str:
    tz = ZoneInfo(settings.timezone)
    local_dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def _profile_text(user, summary: dict[str, object]) -> str:
    username = f"@{user.username}" if user.username else t("common.none")
    return t(
        "profile.body",
        telegram_id=user.telegram_id,
        username=username,
        basic=summary["basic_remaining_seconds"],
        topup=summary["topup_remaining_seconds"],
        refill=_format_refill(summary["next_basic_refill_at"]),
        timezone=settings.timezone,
        used=summary["basic_used_seconds"],
        basic_limit=summary["basic_monthly_seconds"],
    )


def _packages_admin_text(packages, admin_contact: str | None) -> str:
    lines = [t("profile.topup_admin.header")]
    for pkg in packages:
        lines.append(
            t(
                "profile.topup_admin.item",
                package_key=pkg.package_key,
                seconds=pkg.seconds,
                attempts=pkg.approx_attempts_5s,
                price=pkg.manual_price_uzs,
            )
        )
    admin_tag = admin_contact or settings.admin_contact_username or t("profile.topup_admin.default_admin")
    lines.append(t("profile.topup_admin.contact"))
    lines.append(admin_tag)
    lines.append(t("profile.topup_admin.footer"))
    return "\n".join(lines)


def _packages_stars_text(packages) -> str:
    lines = [t("profile.topup_stars.header")]
    for pkg in packages:
        lines.append(
            t(
                "profile.topup_stars.item",
                package_key=pkg.package_key,
                seconds=pkg.seconds,
                attempts=pkg.approx_attempts_5s,
                price=pkg.stars_price,
            )
        )
    lines.append(t("profile.topup_stars.footer"))
    return "\n".join(lines)


async def _render_profile(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        summary = await get_profile_summary(session, user.id)
    await message.answer(_profile_text(user, summary), reply_markup=profile_refresh_kb())


@router.message(F.text == b("menu.profile"))
async def profile_menu(message: Message) -> None:
    await _render_profile(message)


@router.message(F.text == "/profile")
async def profile_command(message: Message) -> None:
    await _render_profile(message)


@router.callback_query(F.data == "profile:refresh")
async def profile_refresh(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session, callback.from_user.id, callback.from_user.username
        )
        summary = await get_profile_summary(session, user.id)
    try:
        await callback.message.edit_text(_profile_text(user, summary), reply_markup=profile_refresh_kb())
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
    await callback.answer()


@router.callback_query(F.data == "profile:topup:admin")
async def profile_topup_admin(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        packages = [pkg for pkg in await list_packages(session) if pkg.is_active]
        admin_contact = await get_admin_contact_username(session)
    await callback.message.edit_text(
        _packages_admin_text(packages, admin_contact), reply_markup=profile_back_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "profile:topup:stars")
async def profile_topup_stars(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        packages = [pkg for pkg in await list_packages(session) if pkg.is_active]
    keys = [pkg.package_key for pkg in packages]
    await callback.message.edit_text(
        _packages_stars_text(packages), reply_markup=stars_packages_kb(keys)
    )
    await callback.answer()


@router.callback_query(F.data == "credits:topup")
async def credits_topup_prompt(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        t("credits.topup_prompt"),
        reply_markup=credits_topup_methods_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:stars:"))
async def profile_stars_invoice(callback: CallbackQuery) -> None:
    package_id = callback.data.split(":")[-1]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        package = await get_active_package(session, package_id.upper())
        if not package:
            await callback.answer(t("profile.package_inactive"), show_alert=True)
            return
        try:
            payment = await create_pending_payment(session, user.id, package.package_key)
        except ValueError:
            await callback.answer(t("profile.package_inactive"), show_alert=True)
            return
    prices = [
        LabeledPrice(
            label=t("profile.invoice_label", package_key=package.package_key),
            amount=payment.amount_stars,
        )
    ]
    try:
        await callback.message.answer_invoice(
            title=t("profile.invoice_title", package_key=package.package_key),
            description=t("profile.invoice_description", seconds=package.seconds),
            payload=payment.payload,
            provider_token="",
            currency="XTR",
            prices=prices,
        )
    except Exception:
        async with AsyncSessionLocal() as session:
            await mark_failed(session, payment.payload, status="failed")
        await callback.message.answer(
            t("payments.unavailable")
        )
    await callback.answer()


@router.pre_checkout_query()
async def stars_pre_checkout(pre_checkout: PreCheckoutQuery) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StarsPayment).where(StarsPayment.payload == pre_checkout.invoice_payload)
        )
        payment = result.scalar_one_or_none()
    if not payment or payment.status not in {"pending", "paid"}:
        await pre_checkout.answer(ok=False, error_message=t("payments.not_found"))
        return
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def stars_success_payment(message: Message) -> None:
    payload = message.successful_payment.invoice_payload
    telegram_charge_id = message.successful_payment.telegram_payment_charge_id
    raw_update = message.model_dump()
    async with AsyncSessionLocal() as session:
        seconds = await credit_paid_payment(
            session,
            payload=payload,
            telegram_charge_id=telegram_charge_id,
            raw_update=raw_update,
        )
    if seconds is None:
        return
    if seconds == 0:
        await message.answer(t("payments.already_confirmed"))
        return
    await message.answer(
        t("payments.success", seconds=seconds)
    )
