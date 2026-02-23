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
from app.bot.keyboards.credits import credits_buy_kb
from sqlalchemy import select

from app.bot.keyboards.pronunciation import (
    pronunciation_menu_kb,
    quiz_done_kb,
    quiz_kb,
    results_kb,
    single_mode_kb,
    single_result_kb,
    single_word_kb,
)
from app.config import settings
from app.db.repo.pronunciation_logs import log_pronunciation
from app.db.repo.app_settings import get_pronunciation_max_voice_seconds
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_or_create_user
from app.db.models import Word
from app.db.repo.words import count_words, get_word, list_recent_words, search_words
from app.db.session import AsyncSessionLocal
from app.bot.handlers.word_selection import start_selection
from app.services.feature_flags import is_feature_enabled
from app.services.pronunciation.base import PronunciationEngine
from app.services.pronunciation.stt_engine import STTPronunciationEngine
from app.utils.bad_words import contains_bad_words
from app.services.stt.base import STTProviderError
from app.services.stt.factory import create_stt_provider, current_stt_provider_name
from app.services.i18n import t
from app.db.repo.credits import CreditError, finalize_charge, refund_charge, reserve_credits
from app.db.repo.srs import get_due_words
from app.utils.audio import convert_to_wav, download_voice

router = Router()

PAGE_SIZE = 10
MAX_VOICE_SECONDS = 15
MAX_VOICE_BYTES = 3 * 1024 * 1024
_LOCKS: dict[int, asyncio.Lock] = {}
logger = logging.getLogger("pronunciation")
STT_UNAVAILABLE_MESSAGE = t("stt.unavailable")


class PronunciationStates(StatesGroup):
    menu = State()
    single_select_mode = State()
    search_query = State()
    search_results = State()
    recent_results = State()
    waiting_voice_single = State()
    quiz_active = State()


def _engine() -> PronunciationEngine:
    return STTPronunciationEngine(create_stt_provider())


def _single_prompt(word: str, translation: str) -> str:
    return t("pronunciation.single_prompt", word=word, translation=translation)


def _quiz_prompt(word: str, translation: str, idx: int, total: int) -> str:
    return t(
        "pronunciation.quiz_prompt",
        word=word,
        translation=translation,
        index=idx,
        total=total,
    )


def _verdict_text(verdict: str) -> str:
    if verdict == "correct":
        return t("pronunciation.verdict_correct")
    if verdict == "close":
        return t("pronunciation.verdict_close")
    return t("pronunciation.verdict_wrong")


def _supports_detailed_pron_feedback() -> bool:
    return (current_stt_provider_name() or "").strip().lower() == "azure"


def _format_percent(value: object) -> str:
    if isinstance(value, (int, float)):
        bounded = max(0.0, min(100.0, float(value)))
        return f"{int(round(bounded))}%"
    return t("common.none")


def _extract_pron_assessment(debug: dict | None) -> dict | None:
    if not isinstance(debug, dict):
        return None
    pa = debug.get("pronunciation_assessment")
    return pa if isinstance(pa, dict) else None


def _overall_score_100(*, score_0_to_1: float | None, debug: dict | None) -> int | None:
    pa = _extract_pron_assessment(debug)
    if isinstance(pa, dict):
        raw = pa.get("pron_score")
        if isinstance(raw, (int, float)):
            return int(round(max(0.0, min(100.0, float(raw)))))
    if isinstance(score_0_to_1, (int, float)):
        return int(round(max(0.0, min(1.0, float(score_0_to_1))) * 100))
    return None


def _error_type_label(raw: str) -> str:
    normalized = (raw or "").strip().lower()
    mapping = {
        "": t("pronunciation.error_none"),
        "none": t("pronunciation.error_none"),
        "mispronunciation": t("pronunciation.error_mispronunciation"),
        "omission": t("pronunciation.error_omission"),
        "insertion": t("pronunciation.error_insertion"),
        "unexpectedbreak": t("pronunciation.error_unexpected_break"),
        "missingbreak": t("pronunciation.error_missing_break"),
        "monotone": t("pronunciation.error_monotone"),
    }
    return mapping.get(normalized, raw or t("common.none"))


def _build_assessment_details(debug: dict | None) -> str:
    pa = _extract_pron_assessment(debug)
    if not isinstance(pa, dict):
        return ""

    pron_score = pa.get("pron_score")
    accuracy_score = pa.get("accuracy_score")
    fluency_score = pa.get("fluency_score")
    completeness_score = pa.get("completeness_score")
    prosody_score = pa.get("prosody_score")

    lines: list[str] = []
    if isinstance(pron_score, (int, float)):
        lines.append(t("pronunciation.assessment_overall", score=_format_percent(pron_score)))

    breakdown_parts: list[str] = []
    if isinstance(accuracy_score, (int, float)):
        breakdown_parts.append(
            t("pronunciation.assessment_part_accuracy", score=_format_percent(accuracy_score))
        )
    if isinstance(fluency_score, (int, float)):
        breakdown_parts.append(
            t("pronunciation.assessment_part_fluency", score=_format_percent(fluency_score))
        )
    if isinstance(completeness_score, (int, float)):
        breakdown_parts.append(
            t("pronunciation.assessment_part_completeness", score=_format_percent(completeness_score))
        )
    if isinstance(prosody_score, (int, float)):
        breakdown_parts.append(
            t("pronunciation.assessment_part_prosody", score=_format_percent(prosody_score))
        )
    if breakdown_parts:
        lines.append(t("pronunciation.assessment_breakdown", values=" | ".join(breakdown_parts)))

    words = pa.get("words")
    if isinstance(words, list) and words:
        preview: list[str] = []
        for item in words[:6]:
            if not isinstance(item, dict):
                continue
            word = str(item.get("word") or "").strip()
            if not word:
                continue
            acc = _format_percent(item.get("accuracy_score"))
            err_label = _error_type_label(str(item.get("error_type") or ""))
            preview.append(
                t(
                    "pronunciation.assessment_word_item",
                    word=word,
                    score=acc,
                    error=err_label,
                )
            )
        if preview:
            lines.append(t("pronunciation.assessment_words", values=", ".join(preview)))

    phonemes = pa.get("weak_phonemes")
    if isinstance(phonemes, list) and phonemes:
        preview: list[str] = []
        for item in phonemes[:6]:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("phoneme") or "").strip()
            if not symbol:
                continue
            preview.append(
                t(
                    "pronunciation.assessment_phoneme_item",
                    phoneme=symbol,
                    score=_format_percent(item.get("accuracy_score")),
                )
            )
        if preview:
            lines.append(t("pronunciation.assessment_phonemes", values=", ".join(preview)))

    return "\n".join(lines)


def _build_worst_word_hint(debug: dict | None) -> tuple[str, str, str] | None:
    pa = _extract_pron_assessment(debug)
    if not isinstance(pa, dict):
        return None
    words = pa.get("words")
    if not isinstance(words, list):
        return None
    candidates: list[tuple[float, str, str]] = []
    for item in words:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word") or "").strip()
        if not word:
            continue
        score = item.get("accuracy_score")
        if not isinstance(score, (int, float)):
            continue
        error = str(item.get("error_type") or "").strip()
        candidates.append((float(score), word, error))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    _, word, error = candidates[0]
    error_raw = (error or "").strip().lower()
    return word, error_raw, _error_type_label(error)


def _tip_for_phoneme(symbol: str) -> str:
    normalized = symbol.strip().lower()
    if normalized.startswith("m"):
        return t("pronunciation.tip_m")
    if normalized in {"ey", "eɪ"}:
        return t("pronunciation.tip_ey")
    return t("pronunciation.tip_phoneme_generic", phoneme=symbol)


def _build_simple_tips(debug: dict | None) -> list[str]:
    tips: list[str] = []
    pa = _extract_pron_assessment(debug)
    if not isinstance(pa, dict):
        return tips
    phonemes = pa.get("weak_phonemes")
    if isinstance(phonemes, list):
        for item in phonemes[:4]:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("phoneme") or "").strip()
            if not symbol:
                continue
            tip = _tip_for_phoneme(symbol)
            if tip not in tips:
                tips.append(tip)
            if len(tips) >= 2:
                return tips

    worst = _build_worst_word_hint(debug)
    if worst:
        _, error_raw, error_label = worst
        if error_raw not in {"", "none"}:
            tips.append(t("pronunciation.tip_from_error", error=error_label))
    return tips[:2]


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
    return [{"word_id": w.id, "word": w.word, "translation": w.translation} for w in sample]


def _normalize_transcript(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip()
    if not normalized:
        return ""
    # Punctuation-only transcripts like "." should be treated as not recognized.
    if not any(ch.isalnum() for ch in normalized):
        return ""
    return normalized


def _is_unheard_audio(transcript: str, debug: dict | None) -> bool:
    if not transcript:
        return True
    pa = _extract_pron_assessment(debug)
    if not isinstance(pa, dict):
        return False
    tracked = [
        pa.get("pron_score"),
        pa.get("accuracy_score"),
        pa.get("fluency_score"),
        pa.get("completeness_score"),
    ]
    numeric = [float(v) for v in tracked if isinstance(v, (int, float))]
    if not numeric:
        return False
    all_zero = all(v <= 0.1 for v in numeric)
    compact = transcript.replace(" ", "")
    return all_zero and len(compact) <= 2


async def _current_max_voice_seconds() -> int:
    async with AsyncSessionLocal() as session:
        value = await get_pronunciation_max_voice_seconds(session)
    if value and value > 0:
        settings.pronunciation_max_voice_seconds = value
        return value
    return settings.pronunciation_max_voice_seconds if settings.pronunciation_max_voice_seconds > 0 else MAX_VOICE_SECONDS


async def _start_pron_quiz(
    message: Message,
    state: FSMContext,
    words: list[Word],
    quiz_size: int,
) -> None:
    if not words:
        await _edit_session_message(message, state, t("pronunciation.quiz_no_words"))
        return
    questions = _build_pronunciation_questions(words, max_questions=quiz_size)
    if not questions:
        await _edit_session_message(message, state, t("pronunciation.quiz_no_words"))
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
        _quiz_prompt(first["word"], str(first.get("translation") or ""), 1, total),
        reply_markup=quiz_kb(),
    )
    await state.update_data(
        current_word_id=first["word_id"],
        reference=first["word"],
        reference_translation=str(first.get("translation") or ""),
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
        await callback.message.edit_text(t("common.nothing_found"), reply_markup=single_mode_kb())
        await state.set_state(PronunciationStates.single_select_mode)
        return

    has_next = len(words) > PAGE_SIZE
    words = words[:PAGE_SIZE]
    items = [
        (word.id, t("common.word_pair", word=word.word, translation=word.translation))
        for word in words
    ]
    await state.update_data(context=context, page=page)
    title = (
        t("pronunciation.results_search")
        if context == "search"
        else t("pronunciation.results_recent")
    )
    await callback.message.edit_text(
        t("pronunciation.results_page", title=title, page=page + 1),
        reply_markup=results_kb(items, page, context, has_next),
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
) -> tuple[str, str | None, float | None, dict | None] | None:
    if not message.voice:
        return None
    max_voice_seconds = await _current_max_voice_seconds()
    if message.voice.duration and message.voice.duration > max_voice_seconds:
        text = t("pronunciation.voice_too_long", max_seconds=max_voice_seconds)
        if retry_prompt:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    ogg_path = None
    wav_path = None
    start = None
    reservation_id = None
    db_user_id = None
    try:
        ogg_path, size = await download_voice(message.bot, message.voice)
        if size > MAX_VOICE_BYTES:
            text = t("pronunciation.voice_too_large")
            if retry_prompt:
                text = f"{text}\n\n{retry_prompt}"
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        try:
            wav_path = await convert_to_wav(ogg_path)
        except RuntimeError:
            text = t("pronunciation.voice_process_failed")
            if retry_prompt:
                text = f"{text}\n\n{retry_prompt}"
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        engine = _engine()
        audio_duration_seconds = int(message.voice.duration or 0)
        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(
                session, message.from_user.id, message.from_user.username
            )
            db_user_id = user.id
            reservation = await reserve_credits(
                session,
                db_user_id,
                audio_duration_seconds=audio_duration_seconds,
                provider=current_stt_provider_name(),
            )
            reservation_id = reservation.ledger_id
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
        debug = result.debug if isinstance(result.debug, dict) else None
        if _is_unheard_audio(transcript, debug):
            text = t("pronunciation.voice_not_understood_word", word=reference)
            await _edit_session_message(message, state, text, reply_markup=retry_markup)
            return None
        if contains_bad_words(transcript):
            logger.info("STT_FILTERED user=%s transcript_len=%s", user_id, len(transcript))
            return result.verdict, None, result.score, None
        logger.info(
            "STT_VERDICT user=%s verdict=%s transcript_len=%s",
            user_id,
            result.verdict,
            len(transcript),
        )
        async with AsyncSessionLocal() as session:
            provider_request_id = None
            if result.debug and isinstance(result.debug, dict):
                provider_request_id = result.debug.get("provider_request_id")
            if reservation_id:
                await finalize_charge(session, reservation_id, provider_request_id=provider_request_id)
        return result.verdict, transcript, result.score, debug
    except CreditError as exc:
        logger.warning("STT_CREDIT_ERROR user=%s error=%s", user_id, str(exc))
        text = exc.user_message or t("pronunciation.credit_error")
        if retry_prompt and text != STT_UNAVAILABLE_MESSAGE:
            text = f"{text}\n\n{retry_prompt}"
        reply_markup_final = retry_markup
        if exc.code == "out_of_credit":
            reply_markup_final = credits_buy_kb()
        await _edit_session_message(message, state, text, reply_markup=reply_markup_final)
        return None
    except STTProviderError as exc:
        if start is not None:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("STT_END user=%s status=%s duration_ms=%s", user_id, "error", duration_ms)
        logger.warning("STT_PROVIDER_ERROR user=%s error=%s", user_id, str(exc))
        if reservation_id and exc.user_message == STT_UNAVAILABLE_MESSAGE:
            async with AsyncSessionLocal() as session:
                await refund_charge(session, reservation_id, reason="stt_unavailable")
        text = exc.user_message or t("pronunciation.check_failed")
        if retry_prompt and text != STT_UNAVAILABLE_MESSAGE:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    except Exception:
        if start is not None:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("STT_END user=%s status=%s duration_ms=%s", user_id, "error", duration_ms)
        logger.exception("STT_UNEXPECTED_ERROR user=%s", user_id)
        if reservation_id:
            async with AsyncSessionLocal() as session:
                await refund_charge(session, reservation_id, reason="stt_error")
        text = t("pronunciation.check_failed")
        if retry_prompt:
            text = f"{text}\n\n{retry_prompt}"
        await _edit_session_message(message, state, text, reply_markup=retry_markup)
        return None
    finally:
        paths = [p for p in [ogg_path, wav_path] if p]
        await _cleanup_files(paths)


async def open_pronunciation_menu(message: Message, state: FSMContext) -> None:
    if not settings.pronunciation_enabled:
        await message.answer(t("pronunciation.disabled_global"))
        return
    await state.clear()
    user_id = await _require_user(message)
    if not user_id:
        return
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await message.answer(t("pronunciation.disabled_feature"))
            return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.pronunciation_enabled:
        await message.answer(t("pronunciation.disabled_user"))
        return
    await state.set_state(PronunciationStates.menu)
    await message.answer(t("pronunciation.menu_prompt"), reply_markup=pronunciation_menu_kb())


@router.callback_query(F.data == "pron:menu")
async def pron_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.menu)
    await callback.message.edit_text(t("pronunciation.menu_prompt"), reply_markup=pronunciation_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:menu:back")
async def pron_menu_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.menu)
    await callback.message.edit_text(t("pronunciation.menu_prompt"), reply_markup=pronunciation_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:menu:single")
async def pron_single_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await callback.message.answer(t("pronunciation.disabled_feature"))
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.pronunciation_enabled:
        await callback.message.answer(t("pronunciation.disabled_user"))
        await callback.answer()
        return
    if user_settings.pronunciation_mode not in {"single", "both"}:
        await callback.message.answer(t("pronunciation.mode_only_quiz"))
        await callback.answer()
        return
    await state.set_state(PronunciationStates.single_select_mode)
    await callback.message.edit_text(t("pronunciation.single_title"), reply_markup=single_mode_kb())
    await callback.answer()


@router.callback_query(F.data == "pron:single:recent")
async def pron_single_recent(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.recent_results)
    await _render_results(callback, state, 0, "recent")
    await callback.answer()


@router.callback_query(F.data == "pron:single:search")
async def pron_single_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PronunciationStates.search_query)
    await callback.message.edit_text(t("pronunciation.search_prompt"))
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
        await callback.message.edit_text(t("pronunciation.word_not_found"), reply_markup=single_mode_kb())
        await state.clear()
        await callback.answer()
        return

    await state.set_state(PronunciationStates.waiting_voice_single)
    await state.update_data(
        word_id=word_id_int,
        reference=word.word,
        reference_translation=word.translation,
        context=context,
        page=page_int,
        pron_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _single_prompt(word.word, word.translation),
        reply_markup=single_word_kb(context, page_int),
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
    await callback.message.edit_text(t("pronunciation.back_to_menu"), reply_markup=None)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
    await callback.message.answer(
        t("common.main_menu"),
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
    reference_translation = str(data.get("reference_translation") or "")
    if reference:
        await callback.message.edit_text(
            _single_prompt(reference, reference_translation),
            reply_markup=single_word_kb(context, int(page)),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pron:detail:show:"))
async def pron_detail_show(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, context, page = callback.data.split(":")
    data = await state.get_data()
    default_text = str(data.get("pron_last_default_text") or "")
    detail_text = str(data.get("pron_last_detail_text") or "")
    has_detail = bool(data.get("pron_last_has_detail"))
    if not default_text:
        await callback.answer()
        return
    text = detail_text if has_detail and detail_text else default_text
    await callback.message.edit_text(
        text,
        reply_markup=single_result_kb(
            context,
            int(page),
            has_detail=has_detail,
            detail_open=bool(has_detail and detail_text),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pron:detail:hide:"))
async def pron_detail_hide(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, context, page = callback.data.split(":")
    data = await state.get_data()
    default_text = str(data.get("pron_last_default_text") or "")
    has_detail = bool(data.get("pron_last_has_detail"))
    if not default_text:
        await callback.answer()
        return
    await callback.message.edit_text(
        default_text,
        reply_markup=single_result_kb(context, int(page), has_detail=has_detail, detail_open=False),
    )
    await callback.answer()


async def _handle_single_voice(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reference = data.get("reference")
    reference_translation = str(data.get("reference_translation") or "")
    context = data.get("context", "recent")
    page = int(data.get("page", 0))
    if not reference:
        await _edit_session_message(message, state, t("pronunciation.word_not_found_retry"))
        return
    await _edit_session_message(
        message,
        state,
        f"{t('pronunciation.checking')}\n\n{_single_prompt(reference, reference_translation)}",
    )
    result = await _process_voice(
        message,
        state,
        message.from_user.id,
        reference,
        retry_prompt=_single_prompt(reference, reference_translation),
        retry_markup=single_word_kb(context, page),
    )
    if not result:
        return
    verdict, transcript, score, assessment_debug = result
    if not _supports_detailed_pron_feedback():
        default_text = (
            t(
                "pronunciation.single_result",
                verdict=_verdict_text(verdict),
                transcript=transcript,
            )
            if transcript
            else t(
                "pronunciation.single_result_hidden",
                verdict=_verdict_text(verdict),
            )
        )
        await state.update_data(
            pron_last_default_text=default_text,
            pron_last_detail_text="",
            pron_last_has_detail=False,
        )
        await _edit_session_message(
            message,
            state,
            default_text,
            reply_markup=single_result_kb(context, page, has_detail=False, detail_open=False),
        )
        return

    score100 = _overall_score_100(score_0_to_1=score, debug=assessment_debug)
    tips = _build_simple_tips(assessment_debug)
    tips_items = tips[:2] if tips else [t("pronunciation.tip_generic")]
    tips_bullets = "\n".join(f"• {item}" for item in tips_items)
    worst_hint = _build_worst_word_hint(assessment_debug)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await log_pronunciation(
            session,
            user.id,
            verdict=verdict,
            reference_word=reference,
            mode="single",
        )

    score_value = score100 if isinstance(score100, int) else 0
    if score_value >= 75:
        default_text = t(
            "pronunciation.single_feedback_success",
            overall=score_value,
            transcript=transcript or t("common.none"),
            tips_bullets=tips_bullets,
        )
    else:
        worst_block = ""
        if worst_hint:
            worst_word, worst_error_raw, worst_error = worst_hint
            if worst_error_raw not in {"", "none"}:
                worst_block = t(
                    "pronunciation.single_feedback_worst_block",
                    word=worst_word,
                    error=worst_error,
                )
        default_text = t(
            "pronunciation.single_feedback_low",
            overall=score_value,
            transcript=transcript or t("common.none"),
            worst_block=worst_block,
            tips_bullets=tips_bullets,
        )

    detail_block = _build_assessment_details(assessment_debug)
    detail_text = default_text
    has_detail = bool(detail_block)
    if has_detail:
        detail_text = t(
            "pronunciation.single_feedback_detail",
            base=default_text,
            details=detail_block,
        )

    await state.update_data(
        pron_last_default_text=default_text,
        pron_last_detail_text=detail_text if has_detail else "",
        pron_last_has_detail=has_detail,
    )
    await _edit_session_message(
        message,
        state,
        default_text,
        reply_markup=single_result_kb(context, page, has_detail=has_detail, detail_open=False),
    )


@router.callback_query(F.data == "pron:menu:quiz")
async def pron_quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "pronunciation"):
            await callback.message.edit_text(t("pronunciation.disabled_feature"))
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        if not user_settings.pronunciation_enabled:
            await callback.message.edit_text(t("pronunciation.disabled_user"))
            await callback.answer()
            return
        if user_settings.pronunciation_mode not in {"quiz", "both"}:
            await callback.message.edit_text(t("pronunciation.mode_only_single"))
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
            await callback.message.edit_text(t("pronunciation.disabled_feature"))
            await callback.answer()
            return
        user = await get_or_create_user(session, callback.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        total_words = await count_words(session, user.id)
    if not user_settings.pronunciation_enabled:
        await callback.message.edit_text(t("pronunciation.disabled_user"))
        await callback.answer()
        return
    if user_settings.pronunciation_mode not in {"quiz", "both"}:
        await callback.message.edit_text(t("pronunciation.mode_only_single"))
        await callback.answer()
        return
    if total_words < 4:
        await callback.message.edit_text(t("quiz.need_words"))
        await callback.answer()
        return
    await state.clear()
    await start_selection(callback, state, "pron_selected")


async def start_pron_quiz_selected_words(
    message: Message, state: FSMContext, selected_ids: list[int], user_id: int
) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        user_settings = await get_or_create_user_settings(session, user)
        result = await session.execute(
            select(Word)
            .where(Word.user_id == user.id, Word.id.in_(selected_ids))
            .order_by(Word.created_at.desc())
        )
        words = list(result.scalars().all())
    if message.from_user and message.from_user.is_bot:
        await state.update_data(pron_message_id=message.message_id)
    await _start_pron_quiz(message, state, words, user_settings.quiz_words_per_session)


async def _handle_quiz_voice(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    idx = data.get("idx", 0)
    if not questions or idx >= len(questions):
        return
    reference = data.get("reference")
    reference_translation = str(data.get("reference_translation") or "")
    if not reference_translation and idx < len(questions):
        reference_translation = str(questions[idx].get("translation") or "")
    if not reference:
        await _edit_session_message(message, state, t("pronunciation.word_not_found_retry_quiz"))
        return
    await _edit_session_message(
        message,
        state,
        f"{t('pronunciation.scoring')}\n\n{_quiz_prompt(reference, reference_translation, idx + 1, len(questions))}",
    )
    retry_prompt = _quiz_prompt(reference, reference_translation, idx + 1, len(questions))
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
    verdict, transcript, result_score, result_debug = result
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
        t("pronunciation.heard", transcript=transcript)
        if transcript
        else t("pronunciation.hidden_result")
    )
    if _supports_detailed_pron_feedback():
        result_pct = _overall_score_100(score_0_to_1=result_score, debug=result_debug)
        feedback = t(
            "pronunciation.quiz_feedback",
            verdict=_verdict_text(verdict),
            transcript_line=transcript_line,
            result_pct=(f"{result_pct}%" if result_pct is not None else t("common.none")),
            delta=2 if verdict == "correct" else 1 if verdict == "close" else 0,
            score=score,
        )
    else:
        feedback = t(
            "pronunciation.quiz_feedback_simple",
            verdict=_verdict_text(verdict),
            transcript_line=transcript_line,
            delta=2 if verdict == "correct" else 1 if verdict == "close" else 0,
            score=score,
        )

    if next_idx >= total:
        accuracy = (correct / total * 100) if total else 0
        await _edit_session_message(
            message,
            state,
            t(
                "pronunciation.quiz_done",
                correct=correct,
                close=close,
                wrong=wrong,
                score=score,
                accuracy=accuracy,
            ),
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
        reference_translation=str(next_question.get("translation") or ""),
    )
    await _edit_session_message(
        message,
        state,
        f"{feedback}\n\n{_quiz_prompt(next_question['word'], str(next_question.get('translation') or ''), next_idx + 1, total)}",
        reply_markup=quiz_kb(),
    )


@router.callback_query(F.data == "pron:quiz:stop")
async def pron_quiz_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t("pronunciation.quiz_stopped"))
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
    await callback.message.answer(
        t("common.main_menu"),
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
        logger.info(
            "STT_SKIP user=%s state=%s reason=state",
            message.from_user.id,
            current,
        )
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user_settings = await get_or_create_user_settings(session, user)
        if not user_settings.pronunciation_enabled:
            await _edit_session_message(message, state, t("pronunciation.disabled_user"))
            await state.clear()
            return
        if current == PronunciationStates.waiting_voice_single.state and user_settings.pronunciation_mode == "quiz":
            await _edit_session_message(
                message, state, t("pronunciation.mode_only_quiz")
            )
            await state.clear()
            return
        if current == PronunciationStates.quiz_active.state and user_settings.pronunciation_mode == "single":
            await _edit_session_message(
                message, state, t("pronunciation.mode_only_single")
            )
            await state.clear()
            return

    data = await state.get_data()
    if data.get("stt_processing"):
        logger.info("STT_SKIP user=%s reason=processing", message.from_user.id)
        await _edit_session_message(
            message, state, t("pronunciation.processing_wait")
        )
        return

    lock = _LOCKS.setdefault(message.from_user.id, asyncio.Lock())
    if lock.locked():
        logger.info("STT_SKIP user=%s reason=lock", message.from_user.id)
        await _edit_session_message(
            message, state, t("pronunciation.processing_wait")
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
