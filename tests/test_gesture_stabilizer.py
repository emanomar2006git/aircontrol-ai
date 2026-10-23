"""Unit tests for GestureStabilizer (no camera needed).
Run from the main project folder:  python -m unittest tests.test_gesture_stabilizer -v
"""
import unittest

from models.types import GestureType
from recognition.gesture_stabilizer import GestureStabilizer

UP = GestureType.THUMB_UP
DOWN = GestureType.THUMB_DOWN
FIST = GestureType.CLOSED_FIST
NONE = GestureType.NONE


def feed(stabilizer, frames):
    """Give a list of raw gestures to the stabilizer and return the list of stable outputs."""
    return [stabilizer.update(frame) for frame in frames]


class TestGestureStabilizer(unittest.TestCase):
    def test_starts_as_none(self):
        self.assertEqual(GestureStabilizer(3).stable, NONE)

    def test_needs_n_frames_in_a_row(self):
        s = GestureStabilizer(3)
        self.assertEqual(feed(s, [UP, UP, UP, UP]), [NONE, NONE, UP, UP])

    def test_single_wrong_frame_is_ignored(self):
        s = GestureStabilizer(3)
        feed(s, [UP, UP, UP])
        self.assertEqual(feed(s, [DOWN, UP, UP]), [UP, UP, UP])

    def test_flicker_never_gets_through(self):
        s = GestureStabilizer(3)
        self.assertEqual(feed(s, [UP, DOWN, UP, DOWN, UP, DOWN]), [NONE] * 6)

    def test_real_change_is_accepted_after_n_frames(self):
        s = GestureStabilizer(3)
        feed(s, [UP, UP, UP])
        self.assertEqual(feed(s, [FIST, FIST, FIST]), [UP, UP, FIST])

    def test_hand_lost_for_a_moment_keeps_the_gesture(self):
        s = GestureStabilizer(3)
        feed(s, [UP, UP, UP])
        self.assertEqual(feed(s, [NONE, NONE, UP]), [UP, UP, UP])

    def test_hand_gone_for_good_gives_none(self):
        s = GestureStabilizer(3)
        feed(s, [UP, UP, UP])
        self.assertEqual(feed(s, [NONE, NONE, NONE]), [UP, UP, NONE])

    def test_count_restarts_when_candidate_changes(self):
        s = GestureStabilizer(3)
        # DOWN twice, then FIST twice: neither reached 3 in a row
        self.assertEqual(feed(s, [DOWN, DOWN, FIST, FIST]), [NONE] * 4)

    def test_required_frames_one_follows_raw(self):
        s = GestureStabilizer(1)
        self.assertEqual(feed(s, [UP, DOWN, NONE]), [UP, DOWN, NONE])

    def test_reset(self):
        s = GestureStabilizer(2)
        feed(s, [UP, UP])
        s.reset()
        self.assertEqual(s.stable, NONE)
        self.assertEqual(feed(s, [UP]), [NONE])

    def test_invalid_required_frames(self):
        with self.assertRaises(ValueError):
            GestureStabilizer(0)


if __name__ == "__main__":
    unittest.main()
