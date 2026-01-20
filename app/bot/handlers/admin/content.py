from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message, parse_int
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.content import (
    admin_content_detail_kb,
    admin_content_list_kb,
    admin_content_menu_kb,
)
from app.bot.keyboards.admin.users import admin_confirm_kb
from app.db.repo.admin import get_user_by_telegram_id, log_admin_action
from app.db.repo.words import (
    delete_word,
    get_word,
    list_recent_words,
    update_example,
    update_translation,
    update_word_text,
)
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

PAGE_SIZE = 10


@router.callback_query(F.data == "admin:content")
async def admin_content_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text(t("admin_content.menu"), reply_markup=admin_content_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:content:user")
async def admin_content_user_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.content_user)
    await callback.message.edit_text(t("admin_content.prompt_id"))
    await callback.answer()


@router.callback_query(F.data == "admin:content:open")
async def admin_content_open_from_user(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("admin_target_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    await state.update_data(content_user_id=int(user_id), content_page=0)
    await _show_content_page(callback.message, state, int(user_id), 0)
    await callback.answer()


@router.message(AdminStates.content_user)
async def admin_content_user_select(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    telegram_id = parse_int(message.text or "")
    if not telegram_id:
        await message.answer(t("admin_content.invalid_id"))
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(t("admin_content.user_not_found"))
        return
    await state.update_data(content_user_id=user.id, content_page=0)
    await _show_content_page(message, state, user.id, 0)


async def _show_content_page(message: Message, state: FSMContext, user_id: int, page: int) -> None:
    async with AsyncSessionLocal() as session:
        words = await list_recent_words(session, user_id, PAGE_SIZE + 1, page * PAGE_SIZE)
    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [
        (word.id, t("common.word_pair", word=word.word, translation=word.translation))
        for word in words
    ]
    await state.set_state(AdminStates.content_page)
    await state.update_data(content_page=page)
    await message.answer(
        t("admin_content.list_title", page=page + 1),
        reply_markup=admin_content_list_kb(items, page, has_next),
    )


@router.callback_query(F.data.startswith("admin:content:page:"))
async def admin_content_page(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("content_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    page = int(callback.data.split(":")[-1])
    await _show_content_page(callback.message, state, int(user_id), page)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:content:open:"))
async def admin_content_open(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("content_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    word_id = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as session:
        word = await get_word(session, int(user_id), word_id)
    if not word:
        await callback.answer(t("admin_content.word_not_found"))
        return
    await state.update_data(content_word_id=word_id)
    text = t("admin_content.word_detail", word=word.word, translation=word.translation)
    if word.example:
        text += "\n" + t("admin_content.word_example", example=word.example)
    await callback.message.edit_text(text, reply_markup=admin_content_detail_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin:content:back")
async def admin_content_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("content_user_id")
    page = int(data.get("content_page", 0))
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    await _show_content_page(callback.message, state, int(user_id), page)
    await callback.answer()


@router.callback_query(F.data == "admin:content:delete")
async def admin_content_delete_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await callback.message.answer(
        t("admin_content.delete_confirm"),
        reply_markup=admin_confirm_kb("admin:content:confirm_delete", "admin:content:back"),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:confirm_delete")
async def admin_content_delete(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("content_user_id")
    word_id = data.get("content_word_id")
    if not user_id or not word_id:
        await callback.answer(t("admin_content.word_not_selected"))
        return
    async with AsyncSessionLocal() as session:
        await delete_word(session, int(user_id), int(word_id))
        await log_admin_action(
            session,
            callback.from_user.id,
            "word_delete",
            "word",
            str(word_id),
        )
    await callback.message.answer(t("admin_content.deleted"))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:content:edit:"))
async def admin_content_edit_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    field = callback.data.split(":")[-1]
    if field not in {"word", "translation", "example"}:
        await callback.answer()
        return
    await state.set_state(AdminStates.content_edit)
    await state.update_data(content_edit_field=field)
    prompt = t("admin_content.edit_prompt")
    if field == "example":
        prompt = t("admin_content.edit_example_prompt")
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(AdminStates.content_edit)
async def admin_content_edit_apply(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    data = await state.get_data()
    user_id = data.get("content_user_id")
    word_id = data.get("content_word_id")
    field = data.get("content_edit_field")
    if not user_id or not word_id or not field:
        await message.answer(t("admin_content.edit_missing"))
        return
    new_value = (message.text or "").strip()
    async with AsyncSessionLocal() as session:
        if field == "word":
            await update_word_text(session, int(user_id), int(word_id), new_value)
            await log_admin_action(session, message.from_user.id, "word_edit", "word", str(word_id))
        elif field == "translation":
            await update_translation(session, int(user_id), int(word_id), new_value)
            await log_admin_action(
                session, message.from_user.id, "translation_edit", "word", str(word_id)
            )
        elif field == "example":
            example = None if new_value == "-" else new_value
            await update_example(session, int(user_id), int(word_id), example)
            await log_admin_action(session, message.from_user.id, "example_edit", "word", str(word_id))
    await state.set_state(AdminStates.content_page)
    await message.answer(t("admin_content.saved"))
