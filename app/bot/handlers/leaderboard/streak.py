from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.leaderboard.menu import _edit_or_send
from app.bot.keyboards.leaderboard.paging import leaderboard_paging_kb
from app.db.repo.leaderboard import get_top_current_streak, get_top_longest_streak
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.config import settings

router = Router()
PAGE_SIZE = 10


def _render_list(title: str, items: list[dict[str, object]], page: int) -> str:
    if not items:
        return f"{title}\n\nHali reytingda hech kim yo‘q. Birinchi bo‘ling!"
    lines = [f"{title}\n"]
    start = page * PAGE_SIZE
    for idx, item in enumerate(items, start=1 + start):
        lines.append(f"{idx}. {item['label']} — {item['value']}")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("lb:list:streak:"))
async def leaderboard_streak(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        include_all = user.telegram_id in settings.admin_user_ids
        items = await get_top_current_streak(session, page, PAGE_SIZE + 1, include_all=include_all)
    has_next = len(items) > PAGE_SIZE
    items = items[:PAGE_SIZE]
    text = _render_list("🔥 Streak TOP", items, page)
    await _edit_or_send(
        callback.message,
        state,
        text,
        reply_markup=leaderboard_paging_kb("streak", page, has_next),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lb:list:longest:"))
async def leaderboard_longest(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        include_all = user.telegram_id in settings.admin_user_ids
        items = await get_top_longest_streak(session, page, PAGE_SIZE + 1, include_all=include_all)
    has_next = len(items) > PAGE_SIZE
    items = items[:PAGE_SIZE]
    text = _render_list("🏆 Longest Streak", items, page)
    await _edit_or_send(
        callback.message,
        state,
        text,
        reply_markup=leaderboard_paging_kb("longest", page, has_next),
    )
    await callback.answer()
