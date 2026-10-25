"""Tests for measure_ui_speed (fake parts, no camera). Needs a screen: skipped without one."""
import unittest

try:
    import tkinter as tk
except ImportError:
    tk = None

from measure_ui_speed import Timer, report


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Thing:
    def work(self, clock):
        clock.now += 0.25
        return "done"


class TestTimer(unittest.TestCase):
    def test_wrap_adds_up_time_and_keeps_result(self):
        clock = FakeClock()
        timer = Timer(clock=clock)
        thing = Thing()
        timer.wrap(thing, "work", "work")
        self.assertEqual(thing.work(clock), "done")
        thing.work(clock)
        self.assertAlmostEqual(timer.totals["work"], 0.5)
        self.assertEqual(timer.calls["work"], 2)

    def test_report_splits_the_loop(self):
        timer = Timer()
        timer.calls = {"process": 10}
        timer.totals = {"process": 0.5, "camera": 0.1, "detect": 0.3, "show": 0.1, "texts": 0.02}
        text = report(timer, 1.0)
        self.assertIn("10.0", text)          # 10 loops in 1 second
        self.assertIn("hand detection       :  30.0 ms", text)
        self.assertIn("waiting inside Tk    :", text)

    def test_report_without_frames(self):
        self.assertIn("No frames", report(Timer(), 1.0))


@unittest.skipIf(tk is None, "Tkinter is not available")
class TestRunWithFakes(unittest.TestCase):
    def test_run_gives_a_report(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no screen available")
        from measure_ui_speed import run
        from tests.fakes import PALM, make_controller
        controller = make_controller([PALM] * 400)[0]
        text = run(controller, seconds=0.5, root=root)
        self.assertIn("FPS of the window loop", text)
        self.assertIn("camera read", text)

    def test_slow_start_does_not_eat_the_measuring_time(self):
        """The camera can take seconds to open: the measuring time must start after that."""
        import time
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no screen available")
        from measure_ui_speed import run
        from tests.fakes import PALM, make_controller
        controller = make_controller([PALM] * 400)[0]
        original_start = controller.start

        def slow_start():
            time.sleep(0.8)             # longer than the measuring time below
            return original_start()

        controller.start = slow_start
        text = run(controller, seconds=0.4, root=root)
        self.assertNotIn("No frames", text)


if __name__ == "__main__":
    unittest.main()
