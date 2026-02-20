import os
import random
import unittest
from datetime import datetime, timedelta


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

    def test_level_path_from_quick_estimate(self) -> None:
        self.assertEqual(level_test.level_path_from("A1"), ("A1", "A2", "B1", "B2", "C1", "C2"))
        self.assertEqual(level_test.level_path_from("B1"), ("B1", "B2", "C1", "C2"))
        self.assertEqual(level_test.level_path_from("C2"), ("C2",))
        self.assertEqual(
            level_test.level_path_from("unknown"),
            ("A1", "A2", "B1", "B2", "C1", "C2"),
        )


if __name__ == "__main__":
    unittest.main()
