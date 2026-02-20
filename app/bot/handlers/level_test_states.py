from aiogram.fsm.state import State, StatesGroup


class LevelTestStates(StatesGroup):
    in_attempt = State()
