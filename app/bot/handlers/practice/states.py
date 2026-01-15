from aiogram.fsm.state import State, StatesGroup


class PracticeStates(StatesGroup):
    menu = State()
    due_confirm = State()
    quick_word = State()
    quick_reveal = State()
    recall_await_answer = State()
    scoring = State()
    done = State()
