from datetime import datetime, timedelta

from app.services.srs import sm2_update


def _approx_days(delta: timedelta) -> int:
    return int(round(delta.total_seconds() / 86400))


def case_good_chain() -> None:
    reps, interval, ef = 0, 0, 2.5
    reps, interval, ef, due_at, lapses = sm2_update(reps, interval, ef, 4)
    assert reps == 1
    assert interval == 1
    assert lapses == 0
    assert _approx_days(due_at - datetime.utcnow()) in {1, 0}

    reps, interval, ef, due_at, lapses = sm2_update(reps, interval, ef, 4)
    assert reps == 2
    assert interval == 6
    assert lapses == 0

    reps, interval, ef, due_at, lapses = sm2_update(reps, interval, ef, 4)
    assert reps == 3
    assert interval == 15
    assert lapses == 0


def case_lapse() -> None:
    reps, interval, ef = 2, 6, 2.5
    reps, interval, ef, due_at, lapses = sm2_update(reps, interval, ef, 0)
    assert reps == 0
    assert interval == 1
    assert lapses == 1
    assert ef >= 1.3
    assert _approx_days(due_at - datetime.utcnow()) in {1, 0}


if __name__ == "__main__":
    case_good_chain()
    case_lapse()
    print("SM-2 tests passed.")
