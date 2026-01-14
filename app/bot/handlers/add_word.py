from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.exc import IntegrityError

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import create_word_with_review, get_word_by_user_word
from app.db.session import AsyncSessionLocal
from app.db.repo.translation_cache import get_cached_translation, save_translation
from app.db.repo.user_settings import get_or_create_user_settings
from app.services.translation import translate
from app.utils.bad_words import contains_bad_words

router = Router()


class AddWordStates(StatesGroup):
    word = State()
    translation_suggest = State()
    example = State()


def _normalize_optional(value: str) -> str | None:
    cleaned = value.strip()
    if cleaned in {"", "yo‘q", "yo'q", "skip"}:
        return None
    return cleaned


def translation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Davom etish", callback_data="translation:accept"),
                InlineKeyboardButton(text="🔄 Boshqa tarjima", callback_data="translation:retry"),
            ],
        ]
    )


def example_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Misolni o‘tkazib yuborish", callback_data="example:skip")]
        ]
    )


async def _finalize_word(message: Message, user_id: int, state: FSMContext) -> None:
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
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
                "🙂 Bu so‘z allaqachon mavjud. Yana bir bor tekshirib ko‘ring."
            )
            await state.clear()
            return
        except Exception:
            await message.answer(
                "⚠️ Nimadir xato ketdi. Yana bir bor urinib ko‘ring 🙂"
            )
            await state.clear()
            return

    await message.answer(
        "✅ Zo‘r! So‘z bazaga qo‘shildi. Endi uni mashqda ko‘ramiz 💪",
        reply_markup=main_menu_kb(),
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
    await message.answer("✍️ Yangi so‘zni yozing (masalan: abandon)")


@router.message(AddWordStates.word)
async def add_word_word(message: Message, state: FSMContext) -> None:
    word = message.text.strip()
    if not word:
        await message.answer("⚠️ So‘z bo‘sh bo‘lmasin. Yana bir bor yozing 🙂")
        return
    if contains_bad_words(word):
        await message.answer(
            "⚠️ Bu so‘zni qabul qila olmayman. Iltimos, boshqa so‘z kiriting 🙂"
        )
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        user_settings = await get_or_create_user_settings(session, user)
        existing = await get_word_by_user_word(session, user.id, word)
        if existing:
            text = (
                "🙂 Bu so‘z avval qo‘shilgan. Mana mavjud yozuv:\n"
                f"So‘z: {existing.word}\n"
                f"Tarjima: {existing.translation}\n"
            )
            if existing.example:
                text += f"Misol: {existing.example}\n"
            if existing.pos:
                text += f"So‘z turkumi: {existing.pos}\n"
            await message.answer(text, reply_markup=main_menu_kb())
            await state.clear()
            return

    await state.update_data(word=word)
    if not user_settings.translation_enabled or not user_settings.auto_translation_suggest:
        await state.update_data(suggested_translation=None)
        await state.set_state(AddWordStates.translation_suggest)
        await message.answer(
            "🤷‍♂️ Avtomatik tarjima o‘chirilgan. Tarjimani yozib yuboring ✍️"
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
            "🤖 Men shu tarjimani topdim:\n"
            f"*{word}* — _{suggestion}_\n\n"
            "Agar to‘g‘ri bo‘lsa, davom etamiz 🙂\n"
            "Agar boshqacha bo‘lsa, to‘g‘ri tarjimani yozib yuboring ✍️",
            reply_markup=translation_kb(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "⚠️ Hozir tarjima tavsiya qila olmadim. Tarjimani yozib yuboring ✍️"
        )


@router.message(AddWordStates.translation_suggest)
async def add_word_translation_message(message: Message, state: FSMContext) -> None:
    translation = message.text.strip()
    if not translation:
        await message.answer("⚠️ Tarjima bo‘sh bo‘lmasin. Yana yozib ko‘ring 🙂")
        return
    if contains_bad_words(translation):
        await message.answer(
            "⚠️ Bu tarjimani qabul qila olmayman. Iltimos, boshqa tarjima yozing 🙂"
        )
        return
    await state.update_data(translation=translation)
    await state.set_state(AddWordStates.example)
    await message.answer(
        "📌 Misol gap bo‘lsa yozing (ixtiyoriy)",
        reply_markup=example_skip_kb(),
    )


@router.callback_query(F.data == "translation:accept")
async def add_word_translation_accept(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    suggestion = data.get("suggested_translation")
    await callback.message.edit_reply_markup(reply_markup=None)
    if not suggestion or contains_bad_words(suggestion):
        await callback.message.answer(
            "🤷‍♂️ Tarjima topilmadi. To‘g‘ri tarjimani yozib yuboring ✍️"
        )
        await callback.answer()
        return
    await state.update_data(translation=suggestion)
    await state.set_state(AddWordStates.example)
    await callback.message.answer(
        "📌 Misol gap bo‘lsa yozing (ixtiyoriy)",
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
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            await callback.answer()
            return
        user_settings = await get_or_create_user_settings(session, user)
    if not user_settings.translation_enabled or not user_settings.auto_translation_suggest:
        await callback.message.answer(
            "🤷‍♂️ Avtomatik tarjima o‘chirilgan. Tarjimani yozib yuboring ✍️"
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
            "🔄 Yana bir variant:\n"
            f"*{word}* — _{suggestion}_\n\n"
            "Agar to‘g‘ri bo‘lsa, davom etamiz 🙂\n"
            "Agar boshqacha bo‘lsa, to‘g‘ri tarjimani yozib yuboring ✍️",
            reply_markup=translation_kb(),
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(
            "⚠️ Hozir tarjima tavsiya qila olmadim. Tarjimani yozib yuboring ✍️"
        )
    await callback.answer()


@router.message(AddWordStates.example)
async def add_word_example(message: Message, state: FSMContext) -> None:
    example = _normalize_optional(message.text)
    if example and contains_bad_words(example):
        await message.answer(
            "⚠️ Bu misolni qabul qila olmayman. Iltimos, boshqasini yozing 🙂"
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
