from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.selection import selection_menu_kb, selection_results_kb
from app.db.models import Word
from app.db.repo.words import list_recent_words, search_words
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

PAGE_SIZE = 10
MIN_SELECTED = 4


class SelectionStates(StatesGroup):
    menu = State()
    search_query = State()
    results = State()


def _parse_callback(data: str) -> tuple[str, str, list[str]] | None:
    parts = data.split(":")
    if len(parts) < 3 or parts[0] != "select":
        return None
    return parts[1], parts[2], parts[3:]


async def _render_menu(
    message: Message, state: FSMContext, purpose: str, selected_ids: list[int]
) -> None:
    await state.set_state(SelectionStates.menu)
    await state.update_data(selection_purpose=purpose, selected_ids=selected_ids)
    await message.edit_text(
        t("selection.menu_title", count=len(selected_ids)),
        reply_markup=selection_menu_kb(purpose, len(selected_ids)),
    )


async def _render_results(
    message: Message,
    state: FSMContext,
    *,
    purpose: str,
    context: str,
    page: int,
    selected_ids: set[int],
    user_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        if context == "search":
            data = await state.get_data()
            query = data.get("search_query", "")
            words = await search_words(
                session, user.id, query, PAGE_SIZE + 1, page * PAGE_SIZE
            )
        elif context == "selected":
            if not selected_ids:
                await _render_menu(message, state, purpose, [])
                return
            result = await session.execute(
                select(Word)
                .where(Word.user_id == user.id, Word.id.in_(selected_ids))
                .order_by(Word.created_at.desc())
                .limit(PAGE_SIZE + 1)
                .offset(page * PAGE_SIZE)
            )
            words = list(result.scalars().all())
        else:
            words = await list_recent_words(
                session, user.id, PAGE_SIZE + 1, page * PAGE_SIZE
            )

    if not words:
        await message.edit_text(
            t("selection.no_words"),
            reply_markup=selection_menu_kb(purpose, len(selected_ids)),
        )
        await state.set_state(SelectionStates.menu)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [
        (word.id, t("common.word_pair", word=word.word, translation=word.translation))
        for word in words
    ]
    title = t(f"selection.title_{context}")
    await state.set_state(SelectionStates.results)
    await state.update_data(
        selection_purpose=purpose,
        selected_ids=list(selected_ids),
        selection_context=context,
        selection_page=page,
    )
    await message.edit_text(
        t("selection.results_title", title=title, page=page + 1),
        reply_markup=selection_results_kb(
            items,
            selected_ids,
            purpose=purpose,
            context=context,
            page=page,
            has_next=has_next,
            selected_count=len(selected_ids),
        ),
    )


async def start_selection(callback: CallbackQuery, state: FSMContext, purpose: str) -> None:
    await _render_menu(callback.message, state, purpose, [])
    await callback.answer()


@router.message(SelectionStates.search_query)
async def selection_search_query(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer(t("selection.search_empty"))
        return
    data = await state.get_data()
    purpose = data.get("selection_purpose")
    selected_ids = set(data.get("selected_ids", []))
    await state.update_data(search_query=query)
    await _render_results(
        message,
        state,
        purpose=purpose,
        context="search",
        page=0,
        selected_ids=selected_ids,
        user_id=message.from_user.id,
    )


@router.callback_query(F.data.startswith("select:"))
async def selection_callback(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = _parse_callback(callback.data)
    if not parsed:
        await callback.answer()
        return
    purpose, action, rest = parsed
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    if data.get("selection_purpose") and data.get("selection_purpose") != purpose:
        selected_ids = set()
    if action == "menu":
        await _render_menu(callback.message, state, purpose, list(selected_ids))
        await callback.answer()
        return
    if action == "back":
        await callback.message.edit_text(t("selection.cancelled"))
        await state.clear()
        await callback.answer()
        return
    if action == "recent":
        await _render_results(
            callback.message,
            state,
            purpose=purpose,
            context="recent",
            page=0,
            selected_ids=selected_ids,
            user_id=callback.from_user.id,
        )
        await callback.answer()
        return
    if action == "search":
        await state.set_state(SelectionStates.search_query)
        await state.update_data(selection_purpose=purpose, selected_ids=list(selected_ids))
        await callback.message.edit_text(t("selection.search_prompt"))
        await callback.answer()
        return
    if action == "view":
        await _render_results(
            callback.message,
            state,
            purpose=purpose,
            context="selected",
            page=0,
            selected_ids=selected_ids,
            user_id=callback.from_user.id,
        )
        await callback.answer()
        return
    if action == "clear":
        await _render_menu(callback.message, state, purpose, [])
        await callback.answer()
        return
    if action == "confirm":
        if len(selected_ids) < MIN_SELECTED:
            await callback.answer(t("selection.min_words"), show_alert=True)
            return
        await state.clear()
        if purpose == "quiz_selected":
            from app.bot.handlers.quiz import start_quiz_selected_words

            await start_quiz_selected_words(
                callback.message, state, list(selected_ids), callback.from_user.id
            )
        elif purpose == "pron_selected":
            from app.bot.handlers.pronunciation import start_pron_quiz_selected_words

            await start_pron_quiz_selected_words(
                callback.message, state, list(selected_ids), callback.from_user.id
            )
        await callback.answer()
        return
    if action == "page":
        if len(rest) < 2:
            await callback.answer()
            return
        context = rest[0]
        page = int(rest[1])
        await _render_results(
            callback.message,
            state,
            purpose=purpose,
            context=context,
            page=page,
            selected_ids=selected_ids,
            user_id=callback.from_user.id,
        )
        await callback.answer()
        return
    if action == "toggle":
        if len(rest) < 3:
            await callback.answer()
            return
        word_id = int(rest[0])
        context = rest[1]
        page = int(rest[2])
        if word_id in selected_ids:
            selected_ids.remove(word_id)
        else:
            selected_ids.add(word_id)
        await _render_results(
            callback.message,
            state,
            purpose=purpose,
            context=context,
            page=page,
            selected_ids=selected_ids,
            user_id=callback.from_user.id,
        )
        await callback.answer()
