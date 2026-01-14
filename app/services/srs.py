from datetime import datetime, timedelta


def schedule_interval(stage: int) -> timedelta:
    if stage <= 0:
        return timedelta(minutes=10)
    if stage == 1:
        return timedelta(days=1)
    if stage == 2:
        return timedelta(days=3)
    if stage == 3:
        return timedelta(days=7)
    if stage == 4:
        return timedelta(days=14)
    return timedelta(days=30)


def next_due_known(stage: int) -> tuple[int, datetime]:
    new_stage = stage + 1
    interval = schedule_interval(new_stage)
    return new_stage, datetime.utcnow() + interval


def next_due_forgot(stage: int) -> tuple[int, datetime]:
    new_stage = max(stage - 1, 0)
    return new_stage, datetime.utcnow() + timedelta(minutes=10)


def next_due_skip(stage: int) -> tuple[int, datetime]:
    return stage, datetime.utcnow() + timedelta(minutes=10)
