from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.leaderboard.menu import _edit_or_send
from app.bot.keyboards.leaderboard.paging import leaderboard_paging_kb
from app.db.repo.leaderboard import get_top_word_count
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.config import settings
from app.services.i18n import t

router = Router()
PAGE_SIZE = 10


def _render_list(items: list[dict[str, object]], page: int) -> str:
    if not items:
        return t("leaderboard.list_empty", title=t("leaderboard.words_title"))
    lines = [t("leaderboard.list_header", title=t("leaderboard.words_title"))]
    start = page * PAGE_SIZE
    for idx, item in enumerate(items, start=1 + start):
        lines.append(
            t(
                "leaderboard.list_item",
                index=idx,
                label=item["label"],
                value=item["value"],
            )
        )
    return "\n".join(lines)


@router.callback_query(F.data.startswith("lb:list:words:"))
async def leaderboard_words(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[-1])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        include_all = user.telegram_id in settings.admin_user_ids
        items = await get_top_word_count(session, page, PAGE_SIZE + 1, include_all=include_all)
    has_next = len(items) > PAGE_SIZE
    items = items[:PAGE_SIZE]
    text = _render_list(items, page)
    await _edit_or_send(
        callback.message,
        state,
        text,
        reply_markup=leaderboard_paging_kb("words", page, has_next),
    )
    await callback.answer()
