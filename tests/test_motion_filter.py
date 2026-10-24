"""Unit tests for MotionFilter (no camera). Run:  python -m unittest tests.test_motion_filter -v"""
import unittest

from models.types import HandData
from recognition.motion_filter import MotionFilter
from tests.test_gesture_recognizer import ALL, CURLED, make_hand


def moved(hand, dx, dy):
    """The same hand shifted by dx, dy (fractions of the image)."""
    return HandData([(x + dx, y + dy, z) for x, y, z in hand.landmarks], hand.aspect_ratio)


def run(motion, hands, fps=30.0, start=0.0):
    """Feed hands one by one; return the list of steady values."""
    steady = []
    for i, hand in enumerate(hands):
        motion.update(hand, start + i / fps)
        steady.append(motion.steady)
    return steady


class TestMotionFilter(unittest.TestCase):
    def setUp(self):
        self.base = make_hand(ALL, "out")   # hand size = 0.256 of the image height

    def test_not_steady_until_there_is_enough_history(self):
        motion = MotionFilter()
        steady = run(motion, [self.base] * 20)
        self.assertFalse(steady[0])
        self.assertFalse(steady[5])      # only 0.17 s of history
        self.assertTrue(steady[-1])

    def test_still_hand_is_steady_at_any_fps(self):
        for fps in (10, 16, 30, 60):
            with self.subTest(fps=fps):
                self.assertTrue(run(MotionFilter(), [self.base] * (fps), fps=fps)[-1])

    def test_small_jitter_is_steady(self):
        hands = [moved(self.base, 0.002 * (-1) ** i, 0.002 * (-1) ** i) for i in range(20)]
        self.assertTrue(run(MotionFilter(), hands)[-1])

    def test_moving_hand_is_not_steady(self):
        hands = [moved(self.base, 0, -0.01 * i) for i in range(20)]   # 0.3 of the image per second
        self.assertFalse(any(run(MotionFilter(), hands)))

    def test_slow_drift_is_still_detected(self):
        hands = [moved(self.base, 0, -0.004 * i) for i in range(30)]  # 0.12 of the image per second
        self.assertFalse(run(MotionFilter(), hands)[-1])

    def test_shape_change_in_place_is_not_steady(self):
        """Closing the hand without moving the wrist must also count as 'not still'."""
        open_hand, fist = make_hand(ALL, "out"), make_hand(CURLED, "tucked")
        hands = [open_hand] * 12 + [fist] * 1 + [fist] * 5
        steady = run(MotionFilter(), hands)
        self.assertTrue(steady[11])        # still before the change
        self.assertFalse(steady[12])       # the change is inside the window
        self.assertFalse(steady[16])
        self.assertTrue(run(MotionFilter(), [open_hand] * 12 + [fist] * 20)[-1])  # still again later

    def test_quick_out_and_back_is_noticed(self):
        hands = [self.base] * 10 + [moved(self.base, 0, -0.1)] + [self.base] * 5
        self.assertFalse(run(MotionFilter(), hands)[-1])

    def test_steady_again_after_the_hand_stops(self):
        moving = [moved(self.base, 0, -0.01 * i) for i in range(10)]
        stopped = [moved(self.base, 0, -0.09)] * 30
        steady = run(MotionFilter(), moving + stopped)
        self.assertFalse(steady[9])
        self.assertTrue(steady[-1])

    def test_hand_lost_resets(self):
        motion = MotionFilter()
        run(motion, [self.base] * 20)
        self.assertTrue(motion.steady)
        self.assertIsNone(motion.update(None, 1.0))
        self.assertFalse(motion.steady)
        self.assertIsNone(motion.change)

    def test_change_is_in_hand_sizes(self):
        motion = MotionFilter(window_seconds=1.0)
        motion.update(self.base, 0.0)
        change = motion.update(moved(self.base, 0, -0.0256), 1.0)    # 0.0256 / 0.256 = 0.1 hand size
        self.assertAlmostEqual(change, 0.1, delta=0.003)

    def test_same_timestamp_and_zero_size_do_not_crash(self):
        motion = MotionFilter()
        motion.update(self.base, 1.0)
        motion.update(self.base, 1.0)
        flat = HandData([(0.5, 0.5, 0.0)] * 21)
        self.assertIsNone(motion.update(flat, 2.0))


if __name__ == "__main__":
    unittest.main()
