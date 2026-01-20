from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.help import help_menu_kb, help_page_kb
from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.db.repo.stats import get_due_count
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import count_words
from app.db.session import AsyncSessionLocal
from app.services.feature_flags import is_feature_enabled
from app.bot.handlers.help_content import HelpContext, build_help_content
from app.services.i18n import t

router = Router()


async def _edit_or_send(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    data = await state.get_data()
    message_id = data.get("help_message_id")
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest:
            pass
    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(help_message_id=sent.message_id)


async def _build_context(user_id: int) -> HelpContext:
    is_admin = user_id in settings.admin_user_ids
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            return HelpContext(
                word_count=0,
                due_count=0,
                quiz_size=10,
                notifications=False,
                notification_time=None,
                pronunciation_enabled=False,
                pronunciation_available=False,
                translation_enabled=False,
                is_admin=is_admin,
                streak=0,
            )
        word_count = await count_words(session, user.id)
        due_count = await get_due_count(session, user.id)
        user_settings = await get_or_create_user_settings(session, user)
        pronunciation_available = await is_feature_enabled(session, "pronunciation")
        translation_enabled = await is_feature_enabled(session, "translation")
        return HelpContext(
            word_count=word_count,
            due_count=due_count,
            quiz_size=user_settings.quiz_words_per_session,
            notifications=user_settings.notifications_enabled,
            notification_time=user_settings.notification_time.strftime("%H:%M")
            if user_settings.notification_time
            else None,
            pronunciation_enabled=user_settings.pronunciation_enabled,
            pronunciation_available=pronunciation_available,
            translation_enabled=translation_enabled,
            is_admin=is_admin,
            streak=user.current_streak,
        )


@router.message(Command("help"))
async def help_entry(message: Message, state: FSMContext) -> None:
    ctx = await _build_context(message.from_user.id)
    await _edit_or_send(
        message,
        state,
        t("help.menu"),
        reply_markup=help_menu_kb(ctx.is_admin),
    )


@router.callback_query(F.data == "help:menu")
async def help_menu(callback: CallbackQuery, state: FSMContext) -> None:
    ctx = await _build_context(callback.from_user.id)
    await _edit_or_send(
        callback.message,
        state,
        t("help.menu"),
        reply_markup=help_menu_kb(ctx.is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "help:exit")
async def help_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(help_message_id=None)
    await callback.message.edit_text(t("help.closed"))
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        streak = user.current_streak if user else 0
    await callback.message.answer(
        t("help.main_menu"),
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("help:"))
async def help_section(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, section, page_str = parts
    if section in {"menu", "exit"}:
        await callback.answer()
        return
    try:
        page = int(page_str)
    except ValueError:
        await callback.answer()
        return

    ctx = await _build_context(callback.from_user.id)
    content = build_help_content(ctx)
    pages = content.get(section)
    if not pages:
        await callback.answer(t("help.section_not_found"))
        return
    if section == "admin" and not ctx.is_admin:
        await callback.answer(t("admin.no_permission"), show_alert=True)
        return
    page = max(0, min(page, len(pages) - 1))
    text = pages[page]
    await _edit_or_send(
        callback.message,
        state,
        text,
        reply_markup=help_page_kb(section, page, len(pages)),
    )
    await callback.answer()
