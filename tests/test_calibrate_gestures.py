"""Tests for calibrate_gestures with a fake camera and fake hands."""
import unittest

import numpy as np

import calibrate_gestures as cal
from models.types import GestureType
from tests.test_gesture_recognizer import ALL, CURLED, make_hand


class TestCalibrateGestures(unittest.TestCase):
    def test_summarize(self):
        records = [(GestureType.CLOSED_FIST, [0.5, 0.6, 0.7, 0.8], -0.1, 0.2, 0.4)] * 9 + \
                  [(GestureType.NONE, [1.0, 1.0, 1.0, 1.0], 0.0, 0.3, 0.5)]
        r = cal.summarize(records, 12)
        self.assertEqual(r["found"], 10)
        self.assertEqual(r["percent"]["CLOSED_FIST"], 90.0)
        self.assertEqual(r["percent"]["NONE"], 10.0)
        self.assertEqual(r["loosest_finger"][0], 0.8)
        self.assertEqual(r["speed"][0], 0.2)
        self.assertEqual(r["shape_change"][0], 0.4)

    def test_no_hand(self):
        self.assertNotIn("percent", cal.summarize([], 30))

    def test_fake_session(self):
        clock = {"t": 0.0}
        hands = {"palm": make_hand(ALL, "out"), "fist": make_hand(CURLED, "tucked"),
                 "none": None}
        state = {"phase": "palm"}

        class Cam:
            def open(self): return True
            def release(self): pass
            def read_frame(self):
                clock["t"] += 1 / 30
                return np.zeros((480, 640, 3), np.uint8)

        class Det:
            def detect(self, frame):
                # phase 1 is seconds 3-5 (after 3 s of "get ready"), phase 2 is seconds 8-10, phase 3 has no hand
                t = clock["t"]
                if t < 6: return hands["palm"]
                if t < 12: return hands["fist"]
                return None
            def draw_landmarks(self, f, h): pass
            def close(self): pass

        phases = [("palm", "palm", 2), ("fist", "fist", 2), ("empty", "nothing", 2)]
        results = cal.main(camera=Cam(), detector=Det(), show=lambda *a: False,
                           clock=lambda: clock["t"], phases=phases)
        self.assertEqual(results["palm"]["percent"]["OPEN_PALM"], 100.0)
        self.assertEqual(results["fist"]["percent"]["CLOSED_FIST"], 100.0)
        self.assertNotIn("percent", results["empty"])
        self.assertAlmostEqual(results["palm"]["fps"], 30, delta=2)
        self.assertLess(results["palm"]["speed"][1], 0.05)         # a still hand
        self.assertLess(results["palm"]["shape_change"][1], 0.05)

    def test_shape_change_is_big_when_the_hand_moves(self):
        a = make_hand(ALL, "out")
        from models.types import HandData
        b = HandData([(x, y - 0.025, z) for x, y, z in a.landmarks], a.aspect_ratio)
        value = cal.pose_change_speed(a, b, 1.0)
        self.assertAlmostEqual(value, 0.025 / 0.256, delta=0.003)
        self.assertIsNone(cal.pose_change_speed(None, b, 1.0))
        self.assertIsNone(cal.pose_change_speed(a, b, 0.0))


if __name__ == "__main__":
    unittest.main()
