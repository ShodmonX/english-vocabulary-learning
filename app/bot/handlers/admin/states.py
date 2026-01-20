from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    menu = State()
    users_search = State()
    srs_confirm = State()
    content_user = State()
    content_page = State()
    content_edit = State()
    credits_add_id = State()
    credits_add_seconds = State()
    credits_forward_seconds = State()
    package_select = State()
    package_edit = State()
    package_seconds = State()
    package_manual_price = State()
    package_stars_price = State()
