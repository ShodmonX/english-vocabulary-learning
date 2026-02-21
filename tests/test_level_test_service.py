import os
import asyncio
import random
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock


os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("ASSEMBLYAI_API_KEY", "test-key")

from app.services import level_test  # noqa: E402


class LevelTestServiceTests(unittest.TestCase):
    def test_selection_ratio_mcq_typing(self) -> None:
        mcq_ids = list(range(1, 100))
        typing_ids = list(range(1000, 1100))
        ordered = level_test.build_question_order(
            mcq_ids,
            typing_ids,
            rng=random.Random(7),
        )
        self.assertEqual(len(ordered), level_test.PLACEMENT_QUESTION_COUNT)
        mcq_count = sum(1 for item in ordered if item < 1000)
        typing_count = sum(1 for item in ordered if item >= 1000)
        self.assertEqual(mcq_count, level_test.PLACEMENT_MCQ_COUNT)
        self.assertEqual(typing_count, level_test.PLACEMENT_TYPING_COUNT)

    def test_timer_expiration_logic(self) -> None:
        now = datetime(2026, 2, 20, 12, 0, 0)
        expired_at = now - timedelta(seconds=1)
        active_until = now + timedelta(seconds=17)

        self.assertTrue(level_test.is_attempt_expired(expired_at, now))
        self.assertEqual(level_test.remaining_seconds(expired_at, now), 0)

        self.assertFalse(level_test.is_attempt_expired(active_until, now))
        self.assertEqual(level_test.remaining_seconds(active_until, now), 17)

    def test_flagged_navigation_is_not_cyclic(self) -> None:
        flagged = [4, 11, 27]
        self.assertEqual(
            level_test.next_flagged_index(flagged, 4, forward=True),
            11,
        )
        self.assertEqual(
            level_test.next_flagged_index(flagged, 27, forward=True),
            None,
        )
        self.assertEqual(
            level_test.next_flagged_index(flagged, 11, forward=False),
            4,
        )
        self.assertEqual(
            level_test.next_flagged_index(flagged, 4, forward=False),
            None,
        )

    def test_score_mapping_boundaries(self) -> None:
        cases = [
            (0.0, "A1"),
            (29.99, "A1"),
            (30.0, "A2"),
            (44.99, "A2"),
            (45.0, "B1"),
            (59.99, "B1"),
            (60.0, "B2"),
            (74.99, "B2"),
            (75.0, "C1"),
            (89.99, "C1"),
            (90.0, "C2"),
            (100.0, "C2"),
        ]
        for score, expected in cases:
            self.assertEqual(level_test.score_to_level(score), expected)

    def test_normalize_level_tag(self) -> None:
        self.assertEqual(level_test.normalize_level_tag("A1"), "A1")
        self.assertEqual(level_test.normalize_level_tag("b2"), "B2")
        self.assertEqual(level_test.normalize_level_tag("unknown"), "A1")

    def test_full_mode_helpers(self) -> None:
        self.assertEqual(level_test.full_mode_for_level("a1"), "FULL_A1")
        self.assertTrue(level_test.is_full_mode("FULL_A2"))
        self.assertEqual(level_test.full_stage_from_mode("FULL_B1"), "B1")
        self.assertEqual(level_test.next_stage("A1"), "A2")
        self.assertIsNone(level_test.next_stage("C2"))

    def test_full_stage_pass_threshold(self) -> None:
        self.assertTrue(
            level_test.is_full_stage_passed(
                mode="FULL_A1",
                status=level_test.STATUS_FINISHED,
                score_pct=85.0,
            )
        )
        self.assertFalse(
            level_test.is_full_stage_passed(
                mode="FULL_A1",
                status=level_test.STATUS_FINISHED,
                score_pct=60.0,
            )
        )

    def test_split_question_counts_sum_and_balance(self) -> None:
        mcq, typing = level_test.split_question_counts(30)
        self.assertEqual(mcq + typing, 30)
        self.assertGreaterEqual(mcq, 1)
        self.assertGreaterEqual(typing, 1)

    def test_runtime_time_limits_are_used(self) -> None:
        with mock.patch.object(level_test.settings, "placement_time_limit_seconds", 777):
            self.assertEqual(
                level_test.time_limit_for_mode(level_test.PLACEMENT_MODE),
                777,
            )
        with mock.patch.object(level_test.settings, "full_time_limit_seconds", 1234):
            self.assertEqual(
                level_test.time_limit_for_mode("FULL_A1"),
                1234,
            )

    def test_full_access_advances_to_next_stage_after_pass(self) -> None:
        attempts = [
            SimpleNamespace(
                mode="FULL_A1",
                status=level_test.STATUS_FINISHED,
                score_pct=85.0,
            )
        ]

        async def fake_list(*args, **kwargs):
            return attempts

        with mock.patch.object(
            level_test.repo,
            "list_completed_full_attempts_in_period",
            side_effect=fake_list,
        ):
            decision = asyncio.run(
                level_test.evaluate_full_access(
                    session=None,
                    user_id=1,
                    quick_level_tag="A1",
                )
            )

        self.assertEqual(decision.start_level, "A2")
        self.assertTrue(decision.free_available)

    def test_full_access_stays_on_failed_stage_and_consumes_free(self) -> None:
        attempts = [
            SimpleNamespace(
                mode="FULL_A1",
                status=level_test.STATUS_FINISHED,
                score_pct=85.0,
            ),
            SimpleNamespace(
                mode="FULL_A2",
                status=level_test.STATUS_FINISHED,
                score_pct=70.0,
            ),
        ]

        async def fake_list(*args, **kwargs):
            return attempts

        with mock.patch.object(
            level_test.repo,
            "list_completed_full_attempts_in_period",
            side_effect=fake_list,
        ):
            decision = asyncio.run(
                level_test.evaluate_full_access(
                    session=None,
                    user_id=1,
                    quick_level_tag="A1",
                )
            )

        self.assertEqual(decision.start_level, "A2")
        self.assertFalse(decision.free_available)


if __name__ == "__main__":
    unittest.main()
