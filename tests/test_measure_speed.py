"""Tests for measure_speed.measure (fake clock and fake camera, no hardware)."""
import unittest

import numpy as np

from measure_speed import measure


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestMeasure(unittest.TestCase):
    def test_reports_fps_and_stage_times(self):
        clock = FakeClock()
        image = np.zeros((10, 10, 3), dtype=np.uint8)

        def read():
            clock.now += 0.05      # camera takes 50 ms
            return image

        def detect(frame):
            clock.now += 0.02      # detection takes 20 ms
            return None

        result = measure(read, detect, seconds=1.0, clock=clock)
        self.assertAlmostEqual(result["camera"], 50.0, places=3)
        self.assertAlmostEqual(result["detect"], 20.0, places=3)
        self.assertAlmostEqual(result["fps"], 1000 / 70, delta=1.5)

    def test_no_frame_gives_none(self):
        self.assertIsNone(measure(lambda: None, seconds=1.0))

if __name__ == "__main__":
    unittest.main()
