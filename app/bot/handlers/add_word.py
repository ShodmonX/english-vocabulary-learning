import json
import random
import html
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.exc import IntegrityError

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import create_word_with_review, get_word_by_user_word
from app.db.session import AsyncSessionLocal
from app.db.repo.translation_cache import get_cached_translation, save_translation
from app.db.repo.user_settings import get_or_create_user_settings
from app.services.feature_flags import is_feature_enabled
from app.services.translation import translate
from app.utils.bad_words import contains_bad_words
from app.services.i18n import b, t

router = Router()
FLOW_MESSAGE_ID_KEY = "add_word_flow_message_id"


class AddWordStates(StatesGroup):
    word = State()
    translation_suggest = State()
    example = State()


def _normalize_optional(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    skip_values = {
        item.strip()
        for item in t("add_word.skip_values").split("|")
        if item.strip()
    }
    if cleaned in skip_values:
        return None
    return cleaned


def translation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("add_word.translation_accept"),
                    callback_data="translation:accept",
                ),
                InlineKeyboardButton(
                    text=b("add_word.translation_retry"),
                    callback_data="translation:retry",
                ),
            ],
        ]
    )


def example_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("add_word.example_skip"), callback_data="example:skip")]
        ]
    )


def _start_prompt_text() -> str:
    examples = _WORD_EXAMPLES or [
        "abandon",
        "curious",
        "improve",
        "journey",
        "reflect",
    ]
    return t("add_word.start_prompt", example=random.choice(examples))


async def _delete_user_message_safe(message: Message) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _delete_message_id_safe(message: Message, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def _clear_flow_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    flow_message_id = data.get(FLOW_MESSAGE_ID_KEY)
    if isinstance(flow_message_id, int):
        await _delete_message_id_safe(message, flow_message_id)
        await state.update_data(**{FLOW_MESSAGE_ID_KEY: None})


async def _upsert_flow_message(
    message: Message,
    state: FSMContext,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    data = await state.get_data()
    flow_message_id = data.get(FLOW_MESSAGE_ID_KEY)
    if isinstance(flow_message_id, int):
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=flow_message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if "message is not modified" in error_text:
                return
            if "message to edit not found" not in error_text and "message can't be edited" not in error_text:
                raise

    sent = await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    await state.update_data(**{FLOW_MESSAGE_ID_KEY: sent.message_id})


async def _finalize_word(message: Message, user_id: int, state: FSMContext) -> None:
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await _clear_flow_message(message, state)
            await message.answer(t("common.start_required"))
            await state.clear()
            return
        try:
            await create_word_with_review(
                session=session,
                user_id=user.id,
                word=data["word"],
                translation=data["translation"],
                example=data.get("example"),
                pos=None,
            )
        except IntegrityError:
            await _clear_flow_message(message, state)
            await message.answer(t("add_word.word_duplicate"))
            await state.clear()
            return
        except Exception:
            await _clear_flow_message(message, state)
            await message.answer(t("add_word.save_error"))
            await state.clear()
            return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        streak = user.current_streak if user else 0
    await _clear_flow_message(message, state)
    safe_word = html.escape(str(data.get("word", "")))
    safe_translation = html.escape(str(data.get("translation", "")))
    result_text = t(
        "add_word.save_success_card",
        word=safe_word,
        translation=safe_translation,
    )
    example = data.get("example")
    if example:
        result_text += "\n" + t(
            "add_word.save_success_example_line",
            example=html.escape(str(example)),
        )
    await message.answer(
        result_text,
        reply_markup=main_menu_kb(
            is_admin=user_id in settings.admin_user_ids, streak=streak
        ),
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data == "menu:add_word")
async def start_add_word(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_add_word_message(callback.message, state)
    await callback.answer()


async def start_add_word_message(message: Message, state: FSMContext) -> None:
    await _clear_flow_message(message, state)
    await state.clear()
    await state.set_state(AddWordStates.word)
    await _delete_user_message_safe(message)
    await _upsert_flow_message(
        message,
        state,
        text=_start_prompt_text(),
    )


_WORD_EXAMPLES = []
_EXAMPLES_PATH = Path(__file__).resolve().parents[2] / "data" / "word_examples.json"


def _load_examples() -> list[str]:
    try:
        data = json.loads(_EXAMPLES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, str) and item.strip()]


_WORD_EXAMPLES = _load_examples()


@router.message(AddWordStates.word)
async def add_word_word(message: Message, state: FSMContext) -> None:
    word = (message.text or "").strip()
    await _delete_user_message_safe(message)
    if not word:
        await _upsert_flow_message(
            message,
            state,
            text=f"{t('add_word.word_empty')}\n\n{_start_prompt_text()}",
        )
        return
    if contains_bad_words(word):
        await _upsert_flow_message(
            message,
            state,
            text=f"{t('add_word.word_rejected')}\n\n{_start_prompt_text()}",
        )
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await _clear_flow_message(message, state)
            await message.answer(t("common.start_required"))
            await state.clear()
            return
        user_settings = await get_or_create_user_settings(session, user)
        existing = await get_word_by_user_word(session, user.id, word)
        if existing:
            lines = [
                t("add_word.word_exists_header"),
                t("add_word.word_line", word=existing.word),
                t("add_word.translation_line", translation=existing.translation),
            ]
            if existing.example:
                lines.append(t("add_word.example_line", example=existing.example))
            if existing.pos:
                lines.append(t("add_word.pos_line", pos=existing.pos))
            await _clear_flow_message(message, state)
            await message.answer(
                "\n".join(lines),
                reply_markup=main_menu_kb(
                    is_admin=message.from_user.id in settings.admin_user_ids,
                    streak=user.current_streak,
                ),
            )
            await state.clear()
            return

    await state.update_data(word=word)
    async with AsyncSessionLocal() as session:
        translation_enabled = await is_feature_enabled(session, "translation")
    if (
        not translation_enabled
        or not user_settings.translation_enabled
        or not user_settings.auto_translation_suggest
    ):
        await state.update_data(suggested_translation=None)
        await state.set_state(AddWordStates.translation_suggest)
        await _upsert_flow_message(
            message,
            state,
            text=t("add_word.translation_disabled"),
        )
        return
    normalized = " ".join(word.lower().split())
    suggestion = None
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user:
            suggestion = await get_cached_translation(session, normalized, "en", "uz")
    if suggestion and contains_bad_words(suggestion):
        suggestion = None
    if not suggestion:
        suggestion = await translate(word)
        if suggestion and contains_bad_words(suggestion):
            suggestion = None
        if suggestion:
            async with AsyncSessionLocal() as session:
                await save_translation(session, word, normalized, "en", "uz", suggestion)
    await state.update_data(suggested_translation=suggestion)
    await state.set_state(AddWordStates.translation_suggest)
    if suggestion:
        safe_word = html.escape(word)
        safe_suggestion = html.escape(suggestion)
        await _upsert_flow_message(
            message,
            state,
            text=t("add_word.translation_found", word=safe_word, suggestion=safe_suggestion),
            reply_markup=translation_kb(),
            parse_mode="HTML",
        )
    else:
        await _upsert_flow_message(
            message,
            state,
            text=t("add_word.translation_missing"),
        )


@router.message(AddWordStates.translation_suggest)
async def add_word_translation_message(message: Message, state: FSMContext) -> None:
    translation = (message.text or "").strip()
    await _delete_user_message_safe(message)
    if not translation:
        await _upsert_flow_message(
            message,
            state,
            text=f"{t('add_word.translation_empty')}\n\n{t('add_word.translation_disabled')}",
        )
        return
    if contains_bad_words(translation):
        await _upsert_flow_message(
            message,
            state,
            text=f"{t('add_word.translation_rejected')}\n\n{t('add_word.translation_disabled')}",
        )
        return
    await state.update_data(translation=translation)
    await state.set_state(AddWordStates.example)
    await _upsert_flow_message(
        message,
        state,
        text=t("add_word.example_prompt"),
        reply_markup=example_skip_kb(),
    )


@router.callback_query(F.data == "translation:accept")
async def add_word_translation_accept(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    suggestion = data.get("suggested_translation")
    if not suggestion or contains_bad_words(suggestion):
        await _upsert_flow_message(
            callback.message,
            state,
            text=t("add_word.translation_not_found"),
        )
        await callback.answer()
        return
    await state.update_data(translation=suggestion)
    await state.set_state(AddWordStates.example)
    await _upsert_flow_message(
        callback.message,
        state,
        text=t("add_word.example_prompt"),
        reply_markup=example_skip_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "translation:retry")
async def add_word_translation_retry(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    word = data.get("word", "")
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await _clear_flow_message(callback.message, state)
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            await callback.answer()
            return
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.translation_enabled or not user_settings.auto_translation_suggest:
        await _upsert_flow_message(
            callback.message,
            state,
            text=t("add_word.translation_disabled"),
        )
        await callback.answer()
        return
    suggestion = await translate(word)
    if suggestion and contains_bad_words(suggestion):
        suggestion = None
    if suggestion:
        normalized = " ".join(word.lower().split())
        async with AsyncSessionLocal() as session:
            await save_translation(session, word, normalized, "en", "uz", suggestion)
    await state.update_data(suggested_translation=suggestion)
    if suggestion:
        safe_word = html.escape(word)
        safe_suggestion = html.escape(suggestion)
        await _upsert_flow_message(
            callback.message,
            state,
            text=t("add_word.translation_retry", word=safe_word, suggestion=safe_suggestion),
            reply_markup=translation_kb(),
            parse_mode="HTML",
        )
    else:
        await _upsert_flow_message(
            callback.message,
            state,
            text=t("add_word.translation_missing"),
        )
    await callback.answer()


@router.message(AddWordStates.example)
async def add_word_example(message: Message, state: FSMContext) -> None:
    await _delete_user_message_safe(message)
    example = _normalize_optional(message.text or "")
    if example and contains_bad_words(example):
        await _upsert_flow_message(
            message,
            state,
            text=f"{t('add_word.example_rejected')}\n\n{t('add_word.example_prompt')}",
            reply_markup=example_skip_kb(),
        )
        return
    await state.update_data(example=example)
    await _finalize_word(message, message.from_user.id, state)


@router.callback_query(F.data == "example:skip")
async def add_word_example_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(example=None)
    await _finalize_word(callback.message, callback.from_user.id, state)
    await callback.answer()
