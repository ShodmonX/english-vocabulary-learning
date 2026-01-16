from __future__ import annotations

import asyncio
import logging
import random
import time
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from app.bot.keyboards.main import main_menu_kb
from sqlalchemy import select

from app.bot.keyboards.pronunciation import (
    pronunciation_menu_kb,
    quiz_done_kb,
    quiz_kb,
    results_kb,
    select_menu_kb,
    select_results_kb,
    single_mode_kb,
    single_result_kb,
    single_word_kb,
)
from app.config import settings
from app.db.repo.pronunciation_logs import get_today_pronunciation_count, log_pronunciation
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_or_create_user
from app.db.models import Word
from app.db.repo.words import get_word, list_recent_words, search_words
from app.db.session import AsyncSessionLocal
from app.services.feature_flags import is_feature_enabled
from app.services.pronunciation.base import PronunciationEngine
from app.services.pronunciation.stt_engine import STTPronunciationEngine
from app.utils.bad_words import contains_bad_words
from app.services.stt.base import STTProviderError
from app.services.stt.local_whisper import LocalWhisperSTT
from app.db.repo.srs import get_due_words
from app.utils.audio import convert_to_wav, download_voice

router = Router()

PAGE_SIZE = 10
MAX_VOICE_SECONDS = 15
MAX_VOICE_BYTES = 3 * 1024 * 1024
_LOCKS: dict[int, asyncio.Lock] = {}
logger = logging.getLogger("pronunciation")


class PronunciationStates(StatesGroup):
    menu = State()
    single_select_mode = State()
    search_query = State()
    search_results = State()
    recent_results = State()
    select_menu = State()
    select_search_query = State()
    select_search_results = State()
    select_recent_results = State()
    select_selected_results = State()
    waiting_voice_single = State()
    quiz_active = State()


def _engine() -> PronunciationEngine:
    return STTPronunciationEngine(LocalWhisperSTT())


def _single_prompt(word: str) -> str:
    return f"🎯 Ayting: *{word}*\n🎙 Voice yuboring (5–10 soniya)."


def _quiz_prompt(word: str, idx: int, total: int) -> str:
    return f"🧩 Talaffuz Quiz — Savol {idx}/{total}\n🎯 Ayting: *{word}*\n🎙 Voice yuboring."


def _verdict_text(verdict: str) -> str:
    if verdict == "correct":
        return "✅ To‘g‘ri"
    if verdict == "close":
        return "🟨 Yaqin"
    return "❌ Noto‘g‘ri"


async def _edit_session_message(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
) -> None:
    data = await state.get_data()
    message_id = data.get("pron_message_id")
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except Exception:
            pass
    sent = await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    await state.update_data(pron_message_id=sent.message_id)


def _build_pronunciation_questions(words: list[object], max_questions: int = 10) -> list[dict[str, object]]:
    if not words:
        return []
    count = min(len(words), max_questions)
    sample = random.sample(words, count)
    return [{"word_id": w.id, "word": w.word} for w in sample]


def _normalize_transcript(text: str) -> str:
    return text.strip() if text else ""


async def _start_pron_quiz(
    message: Message,
    state: FSMContext,
    words: list[Word],
    quiz_size: int,
) -> None:
    if not words:
        await _edit_session_message(message, state, "🫤 Quiz uchun so‘z topilmadi. Avval so‘z qo‘shing.")
        return
    questions = _build_pronunciation_questions(words, max_questions=quiz_size)
    if not questions:
        await _edit_session_message(message, state, "🫤 Quiz uchun so‘z topilmadi. Avval so‘z qo‘shing.")
        return
    total = len(questions)
    await state.set_state(PronunciationStates.quiz_active)
    await state.update_data(
        questions=questions,
        idx=0,
        score=0,
        correct=0,
        close=0,
        wrong=0,
    )
    first = questions[0]
    await message.edit_text(
        _quiz_prompt(first["word"], 1, total), reply_markup=quiz_kb(), parse_mode="Markdown"
    )
    await state.update_data(
        current_word_id=first["word_id"],
        reference=first["word"],
        pron_message_id=message.message_id,
    )


async def _require_user(message: Message) -> int | None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await get_or_create_user_settings(session, user)
        return message.from_user.id


async def _render_results(callback: CallbackQuery, state: FSMContext, page: int, context: str) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await get_or_create_user_settings(session, user)
        if context == "search":
            data = await state.get_data()
            query = data.get("query", "")
            words = await search_words(session, user.id, query, PAGE_SIZE + 1, page * PAGE_SIZE)
        else:
            words = await list_recent_words(session, user.id, PAGE_SIZE + 1, page * PAGE_SIZE)

    if not words:
        await callback.message.edit_text("Hech narsa topilmadi 🙂", reply_markup=single_mode_kb())
        await state.set_state(PronunciationStates.single_select_mode)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, f"{word.word} — {word.translation}") for word in words]
    await state.update_data(context=context, page=page)
    title = "🔎 Natijalar" if context == "search" else "🕒 Oxirgilar"
    await callback.message.edit_text(
        f"{title} ({page + 1}):", reply_markup=results_kb(items, page, context, has_next)
    )


async def _render_select_results(
    message: Message, state: FSMContext, page: int, context: str, user_id: int
) -> None:
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        if context == "search":
            query = data.get("query", "")
            words = await search_words(session, user.id, query, PAGE_SIZE + 1, page * PAGE_SIZE)
        elif context == "selected":
            if not selected_ids:
                await _edit_session_message(
                    message,
                    state,
                    "Tanlangan so‘zlar yo‘q 🙂",
                    reply_markup=select_menu_kb(0),
                )
                await state.set_state(PronunciationStates.select_menu)
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
            words = await list_recent_words(session, user.id, PAGE_SIZE + 1, page * PAGE_SIZE)

    if not words:
        await _edit_session_message(
            message,
            state,
            "Hech narsa topilmadi 🙂",
            reply_markup=select_menu_kb(len(selected_ids)),
        )
        await state.set_state(PronunciationStates.select_menu)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [(word.id, f"{word.word} — {word.translation}") for word in words]
    await state.update_data(context=context, page=page)
    title = "🔎 Natijalar" if context == "search" else "✅ Tanlanganlar" if context == "selected" else "🕒 Oxirgilar"
    await _edit_session_message(
        message,
        state,
        f"{title} ({page + 1}):",
        reply_markup=select_results_kb(items, selected_ids, page, context, has_next, len(selected_ids)),
    )


async def _cleanup_files(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


async def _process_voice(
    message: Message,
    state: FSMContext,
    user_id: int,
    reference: str,
    retry_prompt: str | None = None,
    retry_markup=None,
) -> tuple[str, str | None, int | None] | None:
    if not message.voice:
        return None
    if message.voice.duration and message.voice.duration > MAX_VOICE_SECONDS:
        text = "⏱ Juda uzun. 5–10 soniya yuboring 🙂"
        if retry_prompt:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    ogg_path = None
    wav_path = None
    start = None
    try:
        ogg_path, size = await download_voice(message.bot, message.voice)
        if size > MAX_VOICE_BYTES:
            text = "⏱ Juda katta fayl. 5–10 soniya yuboring 🙂"
            if retry_prompt:
                text = f"{text}\n\n{retry_prompt}"
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        try:
            wav_path = await convert_to_wav(ogg_path)
        except RuntimeError:
            text = "⚠️ Ovozni qayta ishlay olmadim."
            if retry_prompt:
                text = f"{text}\n\n{retry_prompt}"
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        engine = _engine()
        start = time.monotonic()
        logger.info("STT_START user=%s", user_id)
        result = await engine.assess(str(wav_path), reference)
        duration_ms = int((time.monotonic() - start) * 1000)
        transcript_len = len(result.transcript) if result.transcript else 0
        logger.info(
            "STT_END user=%s duration_ms=%s transcript_len=%s",
            user_id,
            duration_ms,
            transcript_len,
        )
        transcript = _normalize_transcript(result.transcript)
        if not transcript:
            text = "🤔 Ovozni tushuna olmadim. Sokin joyda qayta ayting."
            if retry_prompt:
                text = f"{text}\n\n{retry_prompt}"
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        if contains_bad_words(transcript):
            logger.info("STT_FILTERED user=%s transcript_len=%s", user_id, len(transcript))
            return result.verdict, None, None
        logger.info(
            "STT_VERDICT user=%s verdict=%s transcript_len=%s",
            user_id,
            result.verdict,
            len(transcript),
        )
        return result.verdict, transcript, None
    except STTProviderError:
        if start is not None:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("STT_END user=%s status=%s duration_ms=%s", user_id, "error", duration_ms)
        text = "⚠️ Hozir tekshirib bo‘lmadi. Keyinroq urinib ko‘ring 🙂"
        if retry_prompt:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    except Exception:
        if start is not None:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("STT_END user=%s status=%s duration_ms=%s", user_id, "error", duration_ms)
        text = "⚠️ Hozir tekshirib bo‘lmadi. Keyinroq urinib ko‘ring 🙂"
        if retry_prompt:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    finally:
        paths = [p for p in [ogg_path, wav_path] if p]
        await _cleanup_files(paths)


async def open_pronunciation_menu(message: Message, state: FSMContext) -> None:
    if not settings.pronunciation_enabled:
        await message.answer("🫤 Talaffuz hozircha o‘chirib qo‘yilgan.")
        return
    await state.clear()
    user_id = await _require_user(message)
    if not user_id:
        return
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await message.answer("🛑 Hozircha talaffuz o‘chirilgan.")
            return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.pronunciation_enabled:
        await message.answer("🫤 Talaffuz sozlamalarda o‘chirilgan.")
        return
    await state.set_state(PronunciationStates.menu)
    await message.answer("🗣 Talaffuz rejimini tanlang:", reply_markup=pronunciation_menu_kb())


@router.callback_query(F.data == "pron:menu")
async def pron_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.menu)
    await callback.message.edit_text("🗣 Talaffuz rejimini tanlang:", reply_markup=pronunciation_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:menu:back")
async def pron_menu_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.menu)
    await callback.message.edit_text("🗣 Talaffuz rejimini tanlang:", reply_markup=pronunciation_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:menu:single")
async def pron_single_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await callback.message.answer("🛑 Hozircha talaffuz o‘chirilgan.")
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.pronunciation_enabled:
        await callback.message.answer("🫤 Talaffuz sozlamalarda o‘chirilgan.")
        await callback.answer()
        return
    if user_settings.pronunciation_mode not in {"single", "both"}:
        await callback.message.answer("ℹ️ Talaffuz rejimi faqat quiz uchun yoqilgan.")
        await callback.answer()
        return
    await state.set_state(PronunciationStates.single_select_mode)
    await callback.message.edit_text("🎯 Bitta so‘z tekshirish", reply_markup=single_mode_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:single:recent")
async def pron_single_recent(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.recent_results)
    await _render_results(callback, state, 0, "recent")
    await callback.answer()


@router.callback_query(F.data == "pron:single:search")
async def pron_single_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.search_query)
    await callback.message.edit_text("🔎 Qidirish uchun so‘z yozing (masalan: abandon)")
    await callback.answer()




@router.callback_query(F.data.startswith("pron:search:page:"))
async def pron_search_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_results(callback, state, page, "search")
    await callback.answer()


@router.callback_query(F.data.startswith("pron:recent:page:"))
async def pron_recent_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_results(callback, state, page, "recent")
    await callback.answer()


@router.callback_query(F.data.startswith("pron:pick:"))
async def pron_pick_word(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, word_id, context, page = callback.data.split(":")
    word_id_int = int(word_id)
    page_int = int(page)

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        word = await get_word(session, user.id, word_id_int)

    if not word:
        await callback.message.edit_text("So‘z topilmadi 🙂", reply_markup=single_mode_kb())
        await state.clear()
        await callback.answer()
        return

    await state.set_state(PronunciationStates.waiting_voice_single)
    await state.update_data(
        word_id=word_id_int,
        reference=word.word,
        context=context,
        page=page_int,
        pron_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _single_prompt(word.word), reply_markup=single_word_kb(context, page_int), parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pron:single:choose:"))
async def pron_single_choose(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, context, page = callback.data.split(":")
    await _render_results(callback, state, int(page), context)
    await callback.answer()


@router.callback_query(F.data.startswith("pron:back:"))
async def pron_back(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, context, page = callback.data.split(":")
    await _render_results(callback, state, int(page), context)
    await callback.answer()


@router.callback_query(F.data == "pron:exit")
async def pron_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🏁 Menyuga qaytdik", reply_markup=None)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
    await callback.message.answer(
        "Bosh menyu",
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pron:retry:"))
async def pron_retry(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, context, page = callback.data.split(":")
    data = await state.get_data()
    reference = data.get("reference")
    if reference:
        await callback.message.edit_text(
            _single_prompt(reference), reply_markup=single_word_kb(context, int(page)), parse_mode="Markdown"
        )
    await callback.answer()


async def _handle_single_voice(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reference = data.get("reference")
    context = data.get("context", "recent")
    page = int(data.get("page", 0))
    if not reference:
        await _edit_session_message(message, state, "⚠️ So‘z topilmadi. Qayta tanlang 🙂")
        return
    await _edit_session_message(message, state, "⏳ Tekshiryapman…")
    result = await _process_voice(
        message,
        state,
        message.from_user.id,
        reference,
        retry_prompt=_single_prompt(reference),
        retry_markup=single_word_kb(context, page),
    )
    if not result:
        return
    verdict, transcript, _ = result
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await log_pronunciation(
            session,
            user.id,
            verdict=verdict,
            reference_word=reference,
            mode="single",
        )
    if transcript:
        await _edit_session_message(
            message,
            state,
            f"{_verdict_text(verdict)}\n📝 Men eshitganim: {transcript}",
            reply_markup=single_result_kb(context, page),
        )
    else:
        await _edit_session_message(
            message,
            state,
            f"{_verdict_text(verdict)}\n⚠️ Natija xavfsizlik sababli ko‘rsatilmadi.",
            reply_markup=single_result_kb(context, page),
        )


@router.callback_query(F.data == "pron:menu:quiz")
async def pron_quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await callback.message.edit_text("🛑 Hozircha talaffuz o‘chirilgan.")
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        if not user_settings.pronunciation_enabled:
            await callback.message.edit_text("🫤 Talaffuz sozlamalarda o‘chirilgan.")
            await callback.answer()
            return
        if user_settings.pronunciation_mode not in {"quiz", "both"}:
            await callback.message.edit_text("ℹ️ Talaffuz rejimi faqat bitta so‘z uchun yoqilgan.")
            await callback.answer()
            return
        recent_words = await list_recent_words(
            session, user.id, user_settings.quiz_words_per_session, 0
        )
    await _start_pron_quiz(callback.message, state, recent_words, user_settings.quiz_words_per_session)
    await callback.answer()


@router.callback_query(F.data == "pron:menu:select")
async def pron_select_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await callback.message.edit_text("🛑 Hozircha talaffuz o‘chirilgan.")
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.pronunciation_enabled:
        await callback.message.edit_text("🫤 Talaffuz sozlamalarda o‘chirilgan.")
        await callback.answer()
        return
    if user_settings.pronunciation_mode not in {"quiz", "both"}:
        await callback.message.edit_text("ℹ️ Talaffuz rejimi faqat bitta so‘z uchun yoqilgan.")
        await callback.answer()
        return
    await state.set_state(PronunciationStates.select_menu)
    await state.update_data(selected_ids=[], pron_message_id=callback.message.message_id)
    await callback.message.edit_text("🎯 Tanlab talaffuz quiz", reply_markup=select_menu_kb(0))
    await callback.answer()


@router.callback_query(F.data == "pron:select:menu")
async def pron_select_menu_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected = data.get("selected_ids", [])
    await state.set_state(PronunciationStates.select_menu)
    await callback.message.edit_text(
        "🎯 Tanlab talaffuz quiz", reply_markup=select_menu_kb(len(selected))
    )
    await callback.answer()


@router.callback_query(F.data == "pron:select:recent")
async def pron_select_recent(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.select_recent_results)
    await _render_select_results(callback.message, state, 0, "recent", callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "pron:select:search")
async def pron_select_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.select_search_query)
    await callback.message.edit_text("🔎 Qidirish uchun so‘z yozing (masalan: abandon)")
    await callback.answer()


@router.callback_query(F.data == "pron:select:view")
async def pron_select_view(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.select_selected_results)
    await _render_select_results(callback.message, state, 0, "selected", callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("pron:select:toggle:"))
async def pron_select_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, word_id, context, page = callback.data.split(":")
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    word_id_int = int(word_id)
    if word_id_int in selected_ids:
        selected_ids.remove(word_id_int)
    else:
        selected_ids.add(word_id_int)
    await state.update_data(selected_ids=list(selected_ids))
    await _render_select_results(callback.message, state, int(page), context, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("pron:select:recent:page:"))
async def pron_select_recent_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_select_results(callback.message, state, page, "recent", callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("pron:select:search:page:"))
async def pron_select_search_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    await _render_select_results(callback.message, state, page, "search", callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "pron:select:start")
async def pron_select_start(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_ids = data.get("selected_ids", [])
    if len(selected_ids) < 3:
        await callback.message.edit_text(
            "⚠️ Quiz uchun kamida 3 ta so‘z tanlang.",
            reply_markup=select_menu_kb(len(selected_ids)),
        )
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        result = await session.execute(
            select(Word)
            .where(Word.user_id == user.id, Word.id.in_(selected_ids))
            .order_by(Word.created_at.desc())
        )
        words = list(result.scalars().all())
    await _start_pron_quiz(callback.message, state, words, user_settings.quiz_words_per_session)
    await callback.answer()


async def _handle_quiz_voice(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    idx = data.get("idx", 0)
    if not questions or idx >= len(questions):
        return
    reference = data.get("reference")
    if not reference:
        await _edit_session_message(message, state, "⚠️ So‘z topilmadi. Qayta urinib ko‘ring 🙂")
        return
    await _edit_session_message(message, state, "⏳ Baholayapman…")
    retry_prompt = _quiz_prompt(reference, idx + 1, len(questions))
    result = await _process_voice(
        message,
        state,
        message.from_user.id,
        reference,
        retry_prompt=retry_prompt,
        retry_markup=quiz_kb(),
    )
    if not result:
        return
    verdict, transcript, _ = result
    score = data.get("score", 0)
    correct = data.get("correct", 0)
    close = data.get("close", 0)
    wrong = data.get("wrong", 0)
    if verdict == "correct":
        score += 2
        correct += 1
    elif verdict == "close":
        score += 1
        close += 1
    else:
        wrong += 1

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await log_pronunciation(
            session,
            user.id,
            verdict=verdict,
            reference_word=reference,
            mode="quiz",
        )

    next_idx = idx + 1
    total = len(questions)
    transcript_line = (
        f"📝 Men eshitganim: {transcript}"
        if transcript
        else "⚠️ Natija xavfsizlik sababli ko‘rsatilmadi."
    )
    feedback = (
        f"Natija: {_verdict_text(verdict)}\n"
        f"{transcript_line}\n"
        f"⭐ Ball: +{2 if verdict == 'correct' else 1 if verdict == 'close' else 0} | Jami: {score}"
    )

    if next_idx >= total:
        accuracy = (correct / total * 100) if total else 0
        await _edit_session_message(
            message,
            state,
            "🏁 Quiz yakunlandi!\n"
            f"✅ To‘g‘ri: {correct}\n"
            f"🟨 Yaqin: {close}\n"
            f"❌ Noto‘g‘ri: {wrong}\n"
            f"⭐ Jami ball: {score}\n"
            f"📈 Aniqlik: {accuracy:.0f}%\n\n"
            "Ajoyib ish! Davom eting! 💪",
            reply_markup=quiz_done_kb(),
        )
        await state.clear()
        return

    next_question = questions[next_idx]
    await state.update_data(
        idx=next_idx,
        score=score,
        correct=correct,
        close=close,
        wrong=wrong,
        current_word_id=next_question["word_id"],
        reference=next_question["word"],
    )
    await _edit_session_message(
        message,
        state,
        f"{feedback}\n\n{_quiz_prompt(next_question['word'], next_idx + 1, total)}",
        reply_markup=quiz_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "pron:quiz:stop")
async def pron_quiz_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🛑 Quiz to‘xtatildi")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
    await callback.message.answer(
        "Bosh menyu",
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await callback.answer()


@router.message(F.voice)
async def pron_voice_handler(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current not in {
        PronunciationStates.waiting_voice_single.state,
        PronunciationStates.quiz_active.state,
    }:
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        if not user_settings.pronunciation_enabled:
            await _edit_session_message(message, state, "🫤 Talaffuz sozlamalarda o‘chirilgan.")
            await state.clear()
            return
        if current == PronunciationStates.waiting_voice_single.state and user_settings.pronunciation_mode == "quiz":
            await _edit_session_message(
                message, state, "ℹ️ Talaffuz rejimi faqat quiz uchun yoqilgan."
            )
            await state.clear()
            return
        if current == PronunciationStates.quiz_active.state and user_settings.pronunciation_mode == "single":
            await _edit_session_message(
                message, state, "ℹ️ Talaffuz rejimi faqat bitta so‘z uchun yoqilgan."
            )
            await state.clear()
            return
        if user_settings.daily_limit_enabled and user_settings.daily_pronunciation_limit > 0:
            used = await get_today_pronunciation_count(session, user.id)
            if used >= user_settings.daily_pronunciation_limit:
                await _edit_session_message(
                    message, state, "⚠️ Bugungi talaffuz limitiga yetdingiz 🙂"
                )
                return

    data = await state.get_data()
    if data.get("stt_processing"):
        await _edit_session_message(
            message, state, "⏳ Oldingi tekshiruv tugamadi. Iltimos, biroz kuting 🙂"
        )
        return

    lock = _LOCKS.setdefault(message.from_user.id, asyncio.Lock())
    if lock.locked():
        await _edit_session_message(
            message, state, "⏳ Oldingi tekshiruv tugamadi. Iltimos, biroz kuting 🙂"
        )
        return

    await state.update_data(stt_processing=True)
    try:
        async with lock:
            if current == PronunciationStates.waiting_voice_single.state:
                await _handle_single_voice(message, state)
            else:
                await _handle_quiz_voice(message, state)
    finally:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await state.update_data(stt_processing=False)
