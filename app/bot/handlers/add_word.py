from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import IntegrityError

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import create_word_with_review, get_word_by_user_word
from app.db.session import AsyncSessionLocal

router = Router()


class AddWordStates(StatesGroup):
    word = State()
    translation = State()
    example = State()
    pos = State()


def _normalize_optional(value: str) -> str | None:
    cleaned = value.strip()
    if cleaned in {"-", "yo‘q", "yo'q", "skip"}:
        return None
    return cleaned


@router.callback_query(F.data == "menu:add_word")
async def start_add_word(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddWordStates.word)
    await callback.message.answer("So‘z kiriting:")
    await callback.answer()


@router.message(AddWordStates.word)
async def add_word_word(message: Message, state: FSMContext) -> None:
    word = message.text.strip()
    if not word:
        await message.answer("So‘z bo‘sh bo‘lmasin. Qaytadan kiriting:")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Avval /start buyrug‘ini bosing.")
            await state.clear()
            return
        existing = await get_word_by_user_word(session, user.id, word)
        if existing:
            text = (
                "Already exists. Bu so‘z allaqachon mavjud:\n"
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
    await state.set_state(AddWordStates.translation)
    await message.answer("Tarjima kiriting:")


@router.message(AddWordStates.translation)
async def add_word_translation(message: Message, state: FSMContext) -> None:
    translation = message.text.strip()
    if not translation:
        await message.answer("Tarjima bo‘sh bo‘lmasin. Qaytadan kiriting:")
        return

    await state.update_data(translation=translation)
    await state.set_state(AddWordStates.example)
    await message.answer("Misol yozing (ixtiyoriy). Agar yo‘q bo‘lsa, '-' yozing:")


@router.message(AddWordStates.example)
async def add_word_example(message: Message, state: FSMContext) -> None:
    example = _normalize_optional(message.text)
    await state.update_data(example=example)
    await state.set_state(AddWordStates.pos)
    await message.answer("So‘z turkumini yozing (ixtiyoriy). Agar yo‘q bo‘lsa, '-' yozing:")


@router.message(AddWordStates.pos)
async def add_word_pos(message: Message, state: FSMContext) -> None:
    pos = _normalize_optional(message.text)
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Avval /start buyrug‘ini bosing.")
            await state.clear()
            return
        try:
            await create_word_with_review(
                session=session,
                user_id=user.id,
                word=data["word"],
                translation=data["translation"],
                example=data.get("example"),
                pos=pos,
            )
        except IntegrityError:
            await message.answer(
                "Already exists. Bu so‘z allaqachon mavjud. Qaytadan urinib ko‘ring."
            )
            await state.clear()
            return
        except Exception:
            await message.answer("Xatolik yuz berdi. Qaytadan urinib ko‘ring.")
            await state.clear()
            return

    await message.answer("So‘z muvaffaqiyatli qo‘shildi!", reply_markup=main_menu_kb())
    await state.clear()
