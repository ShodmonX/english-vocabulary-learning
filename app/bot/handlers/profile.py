from __future__ import annotations

from datetime import timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.bot.keyboards.profile import profile_back_kb, profile_refresh_kb, stars_packages_kb
from app.config import settings
from sqlalchemy import select

from app.db.models import StarsPayment
from app.db.repo.credits import get_profile_summary
from app.db.repo.packages import get_active_package, list_packages
from app.db.repo.stars_payments import create_pending_payment, credit_paid_payment, mark_failed
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal

router = Router()


def _format_refill(dt) -> str:
    tz = ZoneInfo(settings.timezone)
    local_dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def _profile_text(user, summary: dict[str, object]) -> str:
    username = f"@{user.username}" if user.username else "—"
    return (
        "👤 Profil\n"
        f"ID: {user.telegram_id}\n"
        f"Username: {username}\n\n"
        f"BASIC: {summary['basic_remaining_seconds']}s\n"
        f"TOPUP: {summary['topup_remaining_seconds']}s\n"
        f"Keyingi refill: {_format_refill(summary['next_basic_refill_at'])} ({settings.timezone})\n"
        f"Oy bo‘yicha ishlatilgan: {summary['monthly_used_seconds']}s"
    )


def _packages_admin_text(packages) -> str:
    lines = ["💳 Admin orqali to‘ldirish paketlari:"]
    for pkg in packages:
        lines.append(
            f"\n• {pkg.package_key}: {pkg.seconds}s "
            f"({pkg.approx_attempts_5s} ta ~5s urinish)"
            f"\n  Narx: {pkg.manual_price_uzs} UZS"
        )
    admin_tag = settings.admin_contact_username or "@your_admin"
    lines.append("\n📩 Admin bilan bog‘laning:")
    lines.append(f"{admin_tag}")
    lines.append("\nPaket nomini yozib yuboring: BASIC / STANDARD / PRO")
    return "\n".join(lines)


def _packages_stars_text(packages) -> str:
    lines = ["⭐ Telegram Stars orqali to‘ldirish:"]
    for pkg in packages:
        lines.append(
            f"\n• {pkg.package_key}: {pkg.seconds}s "
            f"({pkg.approx_attempts_5s} ta ~5s urinish)"
            f"\n  Narx: {pkg.stars_price} ⭐"
        )
    lines.append("\nStars orqali to‘lov avtomatik — kredit darhol qo‘shiladi.")
    return "\n".join(lines)


async def _render_profile(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        summary = await get_profile_summary(session, user.id)
    await message.answer(_profile_text(user, summary), reply_markup=profile_refresh_kb())


@router.message(F.text == "👤 Profil")
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
    await callback.message.edit_text(
        _packages_admin_text(packages), reply_markup=profile_back_kb()
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


@router.callback_query(F.data.startswith("profile:stars:"))
async def profile_stars_invoice(callback: CallbackQuery) -> None:
    package_id = callback.data.split(":")[-1]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        package = await get_active_package(session, package_id.upper())
        if not package:
            await callback.answer("Paket mavjud emas yoki o‘chirilgan.", show_alert=True)
            return
        try:
            payment = await create_pending_payment(session, user.id, package.package_key)
        except ValueError:
            await callback.answer("Paket mavjud emas yoki o‘chirilgan.", show_alert=True)
            return
    prices = [LabeledPrice(label=f"{package.package_key} paket", amount=payment.amount_stars)]
    try:
        await callback.message.answer_invoice(
            title=f"{package.package_key} paket",
            description=f"{package.seconds}s top-up krediti",
            payload=payment.payload,
            provider_token="",
            currency="XTR",
            prices=prices,
        )
    except Exception:
        async with AsyncSessionLocal() as session:
            await mark_failed(session, payment.payload, status="failed")
        await callback.message.answer(
            "Hozir to‘lov tizimi vaqtincha ishlamayapti. Keyinroq urinib ko‘ring."
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
        await pre_checkout.answer(ok=False, error_message="To‘lov topilmadi.")
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
        await message.answer("To‘lov allaqachon tasdiqlangan.")
        return
    await message.answer(
        f"To‘lov qabul qilindi. {seconds} sekund TOPUP kreditingizga qo‘shildi."
    )
