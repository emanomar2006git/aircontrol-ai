"""Unit tests for GestureStabilizer (no camera needed).
Run from the main project folder:  python -m unittest tests.test_gesture_stabilizer -v
"""
import unittest

from models.types import GestureType
from recognition.gesture_stabilizer import GestureStabilizer

UP = GestureType.THUMB_UP
DOWN = GestureType.THUMB_DOWN
FIST = GestureType.CLOSED_FIST
PALM = GestureType.OPEN_PALM
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

    def test_volume_gesture_needs_more_frames_than_fist(self):
        s = GestureStabilizer(3, per_gesture={DOWN: 6})
        self.assertEqual(feed(s, [DOWN] * 5), [NONE] * 5)
        self.assertEqual(feed(s, [DOWN]), [DOWN])
        s.reset()
        self.assertEqual(feed(s, [FIST] * 3), [NONE, NONE, FIST])

    def test_closing_hand_moment_is_ignored(self):
        """The thumb points down for 4 frames while the hand closes, then the fist is complete."""
        from recognition.gesture_stabilizer import VOLUME_HOLD
        s = GestureStabilizer(per_gesture=VOLUME_HOLD)
        feed(s, [PALM] * 6)
        out = feed(s, [DOWN] * 6 + [FIST] * 10)
        self.assertNotIn(DOWN, out)
        self.assertEqual(out[-1], FIST)

    def test_play_needs_a_longer_hold_than_volume(self):
        """OPEN_PALM (play) stays long: raising an open hand must not start the video."""
        from recognition.gesture_stabilizer import GESTURE_HOLD
        self.assertGreater(GESTURE_HOLD[PALM], GESTURE_HOLD[UP])
        self.assertGreater(GESTURE_HOLD[PALM], GESTURE_HOLD[DOWN])
        s = GestureStabilizer(per_gesture=GESTURE_HOLD)
        self.assertEqual(feed(s, [PALM] * 9)[-1], NONE)
        self.assertEqual(feed(s, [PALM])[-1], PALM)

    def test_fist_hold_was_tuned_on_a_real_recording(self):
        """Phase 10: with 10 frames the real fist was recognized 3/6 times, with 6 frames 6/6 (same false triggers)."""
        from recognition.gesture_stabilizer import GESTURE_HOLD
        self.assertEqual(GESTURE_HOLD[FIST], 6)
        s = GestureStabilizer(per_gesture=GESTURE_HOLD)
        self.assertEqual(feed(s, [FIST] * 5)[-1], NONE)
        self.assertEqual(feed(s, [FIST])[-1], FIST)


if __name__ == "__main__":
    unittest.main()
