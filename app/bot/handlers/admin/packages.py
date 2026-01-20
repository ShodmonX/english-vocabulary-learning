from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message, parse_int
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.packages import admin_package_edit_kb, admin_packages_menu_kb
from app.db.repo.packages import (
    PackageError,
    get_package,
    list_packages,
    update_package_prices,
)
from app.db.session import AsyncSessionLocal

router = Router()


def _packages_text(packages) -> str:
    lines = ["📦 Paketlar narxi:"]
    for pkg in packages:
        status = "ON" if pkg.is_active else "OFF"
        lines.append(
            f"\n• {pkg.package_key} ({status})"
            f"\n  seconds: {pkg.seconds}"
            f"\n  manual: {pkg.manual_price_uzs} UZS"
            f"\n  stars: {pkg.stars_price} ⭐"
        )
    return "\n".join(lines)


def _package_detail_text(pkg) -> str:
    status = "ON" if pkg.is_active else "OFF"
    return (
        f"📦 {pkg.package_key} ({status})\n"
        f"seconds: {pkg.seconds}\n"
        f"manual: {pkg.manual_price_uzs} UZS\n"
        f"stars: {pkg.stars_price} ⭐"
    )


@router.callback_query(F.data == "admin:packages")
async def admin_packages_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        packages = await list_packages(session)
    await state.set_state(AdminStates.package_select)
    await callback.message.edit_text(_packages_text(packages), reply_markup=admin_packages_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:packages:edit:"))
async def admin_packages_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    package_key = callback.data.split(":")[-1]
    async with AsyncSessionLocal() as session:
        pkg = await get_package(session, package_key)
    if not pkg:
        await callback.answer("Paket topilmadi.", show_alert=True)
        return
    await state.update_data(package_key=pkg.package_key)
    await state.set_state(AdminStates.package_edit)
    await callback.message.edit_text(
        _package_detail_text(pkg), reply_markup=admin_package_edit_kb(pkg.package_key, pkg.is_active)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:packages:manual:"))
async def admin_packages_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    package_key = callback.data.split(":")[-1]
    await state.update_data(package_key=package_key)
    await state.set_state(AdminStates.package_manual_price)
    await callback.message.edit_text("Yangi manual narx (UZS) kiriting:")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:packages:stars:"))
async def admin_packages_stars_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    package_key = callback.data.split(":")[-1]
    await state.update_data(package_key=package_key)
    await state.set_state(AdminStates.package_stars_price)
    await callback.message.edit_text("Yangi Stars narx kiriting:")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:packages:toggle:"))
async def admin_packages_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    _, _, _, package_key, toggle_value = callback.data.split(":")
    is_active = toggle_value == "on"
    async with AsyncSessionLocal() as session:
        try:
            pkg = await update_package_prices(
                session,
                package_key,
                is_active=is_active,
                admin_id=callback.from_user.id,
                reason="toggle",
            )
        except PackageError as exc:
            await callback.answer(exc.user_message or "Xatolik.", show_alert=True)
            return
    await callback.message.edit_text(
        _package_detail_text(pkg), reply_markup=admin_package_edit_kb(pkg.package_key, pkg.is_active)
    )
    await callback.answer("✅ Saqlandi")


@router.message(AdminStates.package_manual_price)
async def admin_packages_manual_save(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    value = parse_int(message.text or "")
    if not value:
        await message.answer("❗ Raqam kiriting.")
        return
    data = await state.get_data()
    package_key = data.get("package_key")
    if not package_key:
        await message.answer("⚠️ Paket topilmadi.")
        return
    async with AsyncSessionLocal() as session:
        try:
            pkg = await update_package_prices(
                session,
                package_key,
                manual_price_uzs=value,
                admin_id=message.from_user.id,
                reason="manual_price",
            )
        except PackageError as exc:
            await message.answer(exc.user_message or "Xatolik.")
            return
    await message.answer(_package_detail_text(pkg), reply_markup=admin_package_edit_kb(pkg.package_key, pkg.is_active))
    await state.set_state(AdminStates.package_edit)


@router.message(AdminStates.package_stars_price)
async def admin_packages_stars_save(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    value = parse_int(message.text or "")
    if not value:
        await message.answer("❗ Raqam kiriting.")
        return
    data = await state.get_data()
    package_key = data.get("package_key")
    if not package_key:
        await message.answer("⚠️ Paket topilmadi.")
        return
    async with AsyncSessionLocal() as session:
        try:
            pkg = await update_package_prices(
                session,
                package_key,
                stars_price=value,
                admin_id=message.from_user.id,
                reason="stars_price",
            )
        except PackageError as exc:
            await message.answer(exc.user_message or "Xatolik.")
            return
    await message.answer(_package_detail_text(pkg), reply_markup=admin_package_edit_kb(pkg.package_key, pkg.is_active))
    await state.set_state(AdminStates.package_edit)
