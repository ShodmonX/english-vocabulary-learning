from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    menu = State()
    learning = State()
    learning_words_per_day = State()
    tests = State()
    tests_quiz_size = State()
    tests_pronunciation_mode = State()
    language = State()
    language_auto_translation = State()
    notifications = State()
    notifications_time = State()
    limits = State()
    limits_pronunciation = State()
    advanced = State()
