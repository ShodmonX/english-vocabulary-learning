from datetime import datetime, timedelta


def initial_ease_factor() -> float:
    return 2.5


def initial_interval_days() -> float:
    return 0.0


def schedule_interval_days(stage: int) -> float:
    if stage <= 0:
        return 10 / 1440
    if stage == 1:
        return 1
    if stage == 2:
        return 3
    if stage == 3:
        return 7
    if stage == 4:
        return 14
    return 30


def _due_at(interval_days: float, ease_factor: float) -> datetime:
    return datetime.utcnow() + timedelta(days=interval_days * ease_factor)


def next_due_known(
    stage: int, ease_factor: float, interval_days: float
) -> tuple[int, float, float, datetime]:
    new_stage = stage + 1
    new_ease = min(ease_factor + 0.05, 3.0)
    new_interval = schedule_interval_days(new_stage)
    return new_stage, new_ease, new_interval, _due_at(new_interval, new_ease)


def next_due_forgot(
    stage: int, ease_factor: float, interval_days: float
) -> tuple[int, float, float, datetime]:
    new_stage = max(stage - 1, 0)
    new_ease = max(ease_factor - 0.2, 1.3)
    new_interval = schedule_interval_days(0)
    return new_stage, new_ease, new_interval, _due_at(new_interval, new_ease)


def next_due_skip(
    stage: int, ease_factor: float, interval_days: float
) -> tuple[int, float, float, datetime]:
    new_interval = schedule_interval_days(0)
    return stage, ease_factor, new_interval, _due_at(new_interval, ease_factor)
