from __future__ import annotations

from datetime import datetime, timedelta


def initial_ease_factor() -> float:
    return 2.5


def initial_interval_days() -> int:
    return 0


def sm2_update(
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    q: int,
) -> tuple[int, int, float, datetime, int]:
    ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if ef < 1.3:
        ef = 1.3

    now = datetime.utcnow()
    lapses = 0

    if q < 3:
        repetitions = 0
        interval_days = 1
        lapses = 1
        due_at = now + timedelta(days=interval_days)
        return repetitions, interval_days, ef, due_at, lapses

    repetitions += 1
    if repetitions == 1:
        interval_days = 1
    elif repetitions == 2:
        interval_days = 6
    else:
        interval_days = max(1, int(round(interval_days * ef)))

    due_at = now + timedelta(days=interval_days)
    return repetitions, interval_days, ef, due_at, lapses
