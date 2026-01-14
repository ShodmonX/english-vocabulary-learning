from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from aiogram import Router

from app.bot.keyboards.pronunciation import results_kb, single_mode_kb
from app.db.repo.users import get_or_create_user
from app.db.repo.words import search_words
from app.db.session import AsyncSessionLocal
from app.bot.handlers.pronunciation import PAGE_SIZE, PronunciationStates

router = Router()


@router.message(PronunciationStates.search_query)
async def pron_search_query(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if not query:
        await message.answer("⚠️ Qidiruv so‘zi bo‘sh bo‘lmasin 🙂")
        return
    await state.update_data(query=query)
    await state.set_state(PronunciationStates.search_results)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        words = await search_words(session, user.id, query, PAGE_SIZE + 1, 0)
    if not words:
        await message.answer("Hech narsa topilmadi 🙂", reply_markup=single_mode_kb())
        await state.set_state(PronunciationStates.single_select_mode)
        return
    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, f"{word.word} — {word.translation}") for word in words]
    await state.update_data(context="search", page=0)
    await message.answer(
        "🔎 Natijalar (1):",
        reply_markup=results_kb(items, 0, "search", has_next),
    )
