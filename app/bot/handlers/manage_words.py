from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.bot.keyboards.manage_words import (
    delete_confirm_kb,
    edit_menu_kb,
    example_skip_kb,
    manage_menu_kb,
    results_kb,
    translation_warning_kb,
    word_detail_kb,
)
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import (
    count_words,
    count_words_today,
    delete_word,
    exists_word,
    find_words_by_translation,
    get_word,
    list_recent_words,
    search_words,
    update_example,
    update_translation,
    update_word_text,
)
from app.db.session import AsyncSessionLocal
from app.utils.bad_words import contains_bad_words

router = Router()

PAGE_SIZE = 10


class ManageStates(StatesGroup):
    menu = State()
    search_query = State()
    search_results = State()
    recent = State()
    word_detail = State()
    edit_word = State()
    edit_translation = State()
    edit_translation_warning = State()
    edit_example = State()


def _word_label(word: str, translation: str) -> str:
    return f"{word} — {translation}"


def _detail_text(word: str, translation: str, example: str | None) -> str:
    text = f"📌 *{word}*\n📝 Ma’nosi: {translation}"
    if example:
        text += f"\n💬 Misol: {example}"
    return text


async def _edit_word_detail(
    callback: CallbackQuery, word_id: int, context: str, page: int, state: FSMContext
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        word = await get_word(session, user.id, word_id)

    if not word:
        await callback.message.edit_text("So‘z topilmadi 🙂", reply_markup=manage_menu_kb())
        await state.set_state(ManageStates.menu)
        return

    await state.update_data(
        word_id=word_id,
        context=context,
        page=page,
        detail_message_id=callback.message.message_id,
    )
    await state.set_state(ManageStates.word_detail)
    await callback.message.edit_text(
        _detail_text(word.word, word.translation, word.example),
        reply_markup=word_detail_kb(word_id, context, page),
        parse_mode="Markdown",
    )


async def _send_word_detail(
    message: Message, user_id: int, word_id: int, context: str, page: int, state: FSMContext
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        word = await get_word(session, user.id, word_id)

    if not word:
        await message.answer("So‘z topilmadi 🙂", reply_markup=manage_menu_kb())
        await state.set_state(ManageStates.menu)
        return

    detail_message_id = (await state.get_data()).get("detail_message_id")
    await state.update_data(
        word_id=word_id,
        context=context,
        page=page,
        detail_message_id=detail_message_id,
    )
    await state.set_state(ManageStates.word_detail)
    if detail_message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=detail_message_id,
            text=_detail_text(word.word, word.translation, word.example),
            reply_markup=word_detail_kb(word_id, context, page),
            parse_mode="Markdown",
        )
    else:
        sent = await message.answer(
            _detail_text(word.word, word.translation, word.example),
            reply_markup=word_detail_kb(word_id, context, page),
            parse_mode="Markdown",
        )
        await state.update_data(detail_message_id=sent.message_id)


async def _require_user(message: Message) -> int | None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            return None
        return user.id


async def _render_search_results(
    callback: CallbackQuery, state: FSMContext, page: int
) -> None:
    data = await state.get_data()
    query = data.get("query", "")
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        words = await search_words(
            session, user.id, query, PAGE_SIZE + 1, page * PAGE_SIZE
        )

    if not words:
        await callback.message.edit_text("Hech narsa topilmadi 🙂", reply_markup=manage_menu_kb())
        await state.set_state(ManageStates.menu)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, _word_label(word.word, word.translation)) for word in words]
    await state.update_data(context="search", page=page)
    await callback.message.edit_text(
        f"🔎 Natijalar ({page + 1}):",
        reply_markup=results_kb(items, page, "search", has_next),
    )


async def _render_search_results_message(
    message: Message, state: FSMContext, page: int
) -> None:
    data = await state.get_data()
    query = data.get("query", "")
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        words = await search_words(
            session, user.id, query, PAGE_SIZE + 1, page * PAGE_SIZE
        )

    if not words:
        await message.answer("Hech narsa topilmadi 🙂", reply_markup=manage_menu_kb())
        await state.set_state(ManageStates.menu)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, _word_label(word.word, word.translation)) for word in words]
    await state.update_data(context="search", page=page)
    await message.answer(
        f"🔎 Natijalar ({page + 1}):",
        reply_markup=results_kb(items, page, "search", has_next),
    )


async def _render_recent_results(
    callback: CallbackQuery, state: FSMContext, page: int
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        words = await list_recent_words(session, user.id, PAGE_SIZE + 1, page * PAGE_SIZE)

    if not words:
        await callback.message.edit_text("Hozircha so‘zlar yo‘q 🙂", reply_markup=manage_menu_kb())
        await state.set_state(ManageStates.menu)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, _word_label(word.word, word.translation)) for word in words]
    await state.update_data(context="recent", page=page)
    await callback.message.edit_text(
        f"🕒 Oxirgilar ({page + 1}):",
        reply_markup=results_kb(items, page, "recent", has_next),
    )


@router.message(F.text == "🗂 So‘zlarim")
async def open_manage_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = await _require_user(message)
    if not user_id:
        return
    async with AsyncSessionLocal() as session:
        total = await count_words(session, user_id)
        today = await count_words_today(session, user_id)
    await state.set_state(ManageStates.menu)
    await message.answer(
        "🗂 So‘zlarni boshqarish\n"
        f"📚 Jami so‘zlar: {total}\n"
        f"✨ Bugun qo‘shilgan: {today}",
        reply_markup=manage_menu_kb(),
    )


@router.callback_query(F.data == "manage:menu")
async def manage_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageStates.menu)
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        total = await count_words(session, user.id)
        today = await count_words_today(session, user.id)
    await callback.message.edit_text(
        "🗂 So‘zlarni boshqarish\n"
        f"📚 Jami so‘zlar: {total}\n"
        f"✨ Bugun qo‘shilgan: {today}",
        reply_markup=manage_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "manage:search")
async def manage_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageStates.search_query)
    await callback.message.edit_text(
        "🔎 Qidirish uchun so‘z yozing (masalan: abandon)."
    )
    await callback.answer()


@router.message(ManageStates.search_query)
async def manage_search_query(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if not query:
        await message.answer("⚠️ Qidiruv so‘zi bo‘sh bo‘lmasin 🙂")
        return
    await state.update_data(query=query)
    await state.set_state(ManageStates.search_results)
    await _render_search_results_message(message, state, 0)


@router.callback_query(F.data.startswith("manage:search:page:"))
async def manage_search_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_search_results(callback, state, page)
    await callback.answer()


@router.callback_query(F.data.startswith("manage:recent:page:"))
async def manage_recent_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_recent_results(callback, state, page)
    await callback.answer()


@router.callback_query(F.data == "manage:recent")
async def manage_recent(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageStates.recent)
    await _render_recent_results(callback, state, 0)
    await callback.answer()


@router.callback_query(F.data.startswith("word:open:"))
async def manage_open_word(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, context, page = callback.data.split(":")
    word_id_int = int(word_id)
    page_int = int(page)

    await _edit_word_detail(callback, word_id_int, context, page_int, state)
    await callback.answer()


@router.callback_query(F.data.startswith("word:back:"))
async def manage_back(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, context, page = callback.data.split(":")
    page_int = int(page)
    if context == "search":
        await _render_search_results(callback, state, page_int)
    else:
        await _render_recent_results(callback, state, page_int)
    await callback.answer()


@router.callback_query(F.data.startswith("word:delete:"))
async def manage_delete_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, context, page = callback.data.split(":")
    await callback.message.edit_text(
        "🗑 Rostdan ham o‘chirmoqchimisiz?",
        reply_markup=delete_confirm_kb(int(word_id), context, int(page)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("word:delete_confirm:"))
async def manage_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, context, page = callback.data.split(":")
    word_id_int = int(word_id)
    page_int = int(page)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await delete_word(session, user.id, word_id_int)

    if context == "search":
        await _render_search_results(callback, state, page_int)
    else:
        await _render_recent_results(callback, state, page_int)
    await callback.answer()


@router.callback_query(F.data.startswith("word:edit:"))
async def manage_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, context, page = callback.data.split(":")
    await state.update_data(word_id=int(word_id), context=context, page=int(page))
    await callback.message.edit_text(
        "Nimani tahrirlaymiz?", reply_markup=edit_menu_kb(int(word_id), context, int(page))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("word:edit_field:"))
async def manage_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, field, word_id, context, page = callback.data.split(":")
    await state.update_data(word_id=int(word_id), context=context, page=int(page))

    if field == "word":
        await state.set_state(ManageStates.edit_word)
        await callback.message.edit_text("✍️ Yangi so‘zni yozing:")
    elif field == "translation":
        await state.set_state(ManageStates.edit_translation)
        await callback.message.edit_text("✍️ Yangi tarjimani yozing:")
    else:
        await state.set_state(ManageStates.edit_example)
        await state.update_data(prompt_message_id=callback.message.message_id)
        await callback.message.edit_text(
            "💬 Yangi misolni yozing:",
            reply_markup=example_skip_kb(int(word_id), context, int(page)),
        )
    await callback.answer()


@router.message(ManageStates.edit_word)
async def manage_edit_word(message: Message, state: FSMContext) -> None:
    new_word = message.text.strip()
    if not new_word:
        await message.answer("⚠️ So‘z bo‘sh bo‘lmasin 🙂")
        return
    if contains_bad_words(new_word):
        await message.answer(
            "⚠️ Bu so‘zni qabul qila olmayman. Iltimos, boshqa so‘z kiriting 🙂"
        )
        return
    data = await state.get_data()
    word_id = data.get("word_id")
    context = data.get("context")
    page = data.get("page", 0)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        exists = await exists_word(session, user.id, new_word, exclude_word_id=word_id)
        if exists:
            await message.answer(
                f"⚠️ Bu so‘z sizda allaqachon bor: {new_word}. Boshqasini kiriting."
            )
            return
        await update_word_text(session, user.id, int(word_id), new_word)

    await message.answer("✅ Yangilandi")
    await _send_word_detail(message, message.from_user.id, int(word_id), context, int(page), state)


@router.message(ManageStates.edit_translation)
async def manage_edit_translation(message: Message, state: FSMContext) -> None:
    new_translation = message.text.strip()
    if not new_translation:
        await message.answer("⚠️ Tarjima bo‘sh bo‘lmasin 🙂")
        return
    if contains_bad_words(new_translation):
        await message.answer(
            "⚠️ Bu tarjimani qabul qila olmayman. Iltimos, boshqa tarjima yozing 🙂"
        )
        return
    data = await state.get_data()
    word_id = int(data.get("word_id"))
    context = data.get("context")
    page = int(data.get("page", 0))

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        duplicates = await find_words_by_translation(
            session, user.id, new_translation, exclude_word_id=word_id
        )

    if duplicates:
        other = duplicates[0]
        await state.update_data(pending_translation=new_translation)
        await state.set_state(ManageStates.edit_translation_warning)
        await message.answer(
            "⚠️ Eslatma: bu tarjima boshqa so‘zda ham ishlatilgan:\n"
            f"{other.word} — {other.translation}\n\n"
            "Baribir saqlaysizmi yoki boshqa tarjima kiritasizmi?",
            reply_markup=translation_warning_kb(word_id, context, page),
        )
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await update_translation(session, user.id, word_id, new_translation)

    await message.answer("✅ Yangilandi")
    await _send_word_detail(message, message.from_user.id, word_id, context, page, state)


@router.callback_query(F.data.startswith("word:translation_force:"))
async def manage_translation_force(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pending = data.get("pending_translation")
    if not pending:
        await callback.answer()
        return
    if contains_bad_words(pending):
        await callback.message.answer(
            "⚠️ Bu tarjimani qabul qila olmayman. Iltimos, boshqa tarjima yozing 🙂"
        )
        await state.set_state(ManageStates.edit_translation)
        await callback.answer()
        return
    _, _, word_id, _, _ = callback.data.split(":")
    word_id_int = int(word_id)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await update_translation(session, user.id, word_id_int, pending)

    await callback.message.edit_text("✅ Yangilandi")
    data = await state.get_data()
    context = data.get("context", "recent")
    page = int(data.get("page", 0))
    await _edit_word_detail(callback, word_id_int, context, page, state)
    await callback.answer()


@router.callback_query(F.data.startswith("word:translation_retry:"))
async def manage_translation_retry(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageStates.edit_translation)
    await callback.message.edit_text("✍️ Yangi tarjimani yozing:")
    await callback.answer()


@router.message(ManageStates.edit_example)
async def manage_edit_example(message: Message, state: FSMContext) -> None:
    new_example = message.text.strip()
    data = await state.get_data()
    word_id = int(data.get("word_id"))
    prompt_id = data.get("prompt_message_id")
    if new_example and contains_bad_words(new_example):
        await message.answer(
            "⚠️ Bu misolni qabul qila olmayman. Iltimos, boshqasini yozing 🙂"
        )
        return

    if prompt_id:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id, message_id=prompt_id, reply_markup=None
        )

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await update_example(session, user.id, word_id, new_example)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        streak = user.current_streak if user else 0
    await message.answer(
        "✅ Yangilandi",
        reply_markup=main_menu_kb(
            is_admin=message.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await state.clear()


@router.callback_query(F.data.startswith("word:example_skip:"))
async def manage_example_skip(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, _, _ = callback.data.split(":")
    word_id_int = int(word_id)

    await callback.message.edit_reply_markup(reply_markup=None)

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await update_example(session, user.id, word_id_int, None)

    await callback.message.edit_text("✅ Yangilandi")
    data = await state.get_data()
    context = data.get("context", "recent")
    page = int(data.get("page", 0))
    await _edit_word_detail(callback, word_id_int, context, page, state)
    await callback.answer()
