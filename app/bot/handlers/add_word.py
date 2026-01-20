import json
import random
from pathlib import Path

from aiogram import F, Router
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


async def _finalize_word(message: Message, user_id: int, state: FSMContext) -> None:
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
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
            await message.answer(
                t("add_word.word_duplicate")
            )
            await state.clear()
            return
        except Exception:
            await message.answer(
                t("add_word.save_error")
            )
            await state.clear()
            return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        streak = user.current_streak if user else 0
    await message.answer(
        t("add_word.save_success"),
        reply_markup=main_menu_kb(
            is_admin=message.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await state.clear()


@router.callback_query(F.data == "menu:add_word")
async def start_add_word(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_add_word_message(callback.message, state)
    await callback.answer()


async def start_add_word_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddWordStates.word)
    examples = _WORD_EXAMPLES or [
        "abandon",
        "curious",
        "improve",
        "journey",
        "reflect",
    ]
    await message.answer(
        t("add_word.start_prompt", example=random.choice(examples))
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
    word = message.text.strip()
    if not word:
        await message.answer(t("add_word.word_empty"))
        return
    if contains_bad_words(word):
        await message.answer(
            t("add_word.word_rejected")
        )
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
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
        await message.answer(
            t("add_word.translation_disabled")
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
        await message.answer(
            t("add_word.translation_found", word=word, suggestion=suggestion),
            reply_markup=translation_kb(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            t("add_word.translation_missing")
        )


@router.message(AddWordStates.translation_suggest)
async def add_word_translation_message(message: Message, state: FSMContext) -> None:
    translation = message.text.strip()
    if not translation:
        await message.answer(t("add_word.translation_empty"))
        return
    if contains_bad_words(translation):
        await message.answer(
            t("add_word.translation_rejected")
        )
        return
    await state.update_data(translation=translation)
    await state.set_state(AddWordStates.example)
    await message.answer(
        t("add_word.example_prompt"),
        reply_markup=example_skip_kb(),
    )


@router.callback_query(F.data == "translation:accept")
async def add_word_translation_accept(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    suggestion = data.get("suggested_translation")
    await callback.message.edit_reply_markup(reply_markup=None)
    if not suggestion or contains_bad_words(suggestion):
        await callback.message.answer(
            t("add_word.translation_not_found")
        )
        await callback.answer()
        return
    await state.update_data(translation=suggestion)
    await state.set_state(AddWordStates.example)
    await callback.message.answer(
        t("add_word.example_prompt"),
        reply_markup=example_skip_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "translation:retry")
async def add_word_translation_retry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    word = data.get("word", "")
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            await callback.answer()
            return
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.translation_enabled or not user_settings.auto_translation_suggest:
        await callback.message.answer(
            t("add_word.translation_disabled")
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
        await callback.message.answer(
            t("add_word.translation_retry", word=word, suggestion=suggestion),
            reply_markup=translation_kb(),
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(
            t("add_word.translation_missing")
        )
    await callback.answer()


@router.message(AddWordStates.example)
async def add_word_example(message: Message, state: FSMContext) -> None:
    example = _normalize_optional(message.text)
    if example and contains_bad_words(example):
        await message.answer(
            t("add_word.example_rejected")
        )
        return
    await state.update_data(example=example)
    await _finalize_word(message, message.from_user.id, state)


@router.callback_query(F.data == "example:skip")
async def add_word_example_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(example=None)
    await _finalize_word(callback.message, callback.from_user.id, state)
    await callback.answer()
