"""Tests for accuracy_test.py (no camera): the state machine, the report and the loop."""
import unittest
from types import SimpleNamespace

from accuracy_test import (ACTIVE, AccuracyTest, Recorder, build_report, classify_frame, load_recording,
                           run, run_idle)
from models.types import GestureType

UP, DOWN = GestureType.THUMB_UP, GestureType.THUMB_DOWN
FIST, PALM, NONE = GestureType.CLOSED_FIST, GestureType.OPEN_PALM, GestureType.NONE


def advance_to_active(test, now=0.0):
    """Feed NONE frames until the test asks for the beep. Returns the time of the beep."""
    while True:
        if test.update(NONE, now):
            return now
        now += 0.1


class TestStateMachine(unittest.TestCase):
    def test_sequence_goes_around_the_four_gestures(self):
        test = AccuracyTest(trials_per_gesture=2)
        self.assertEqual(test.sequence[:5], [UP, DOWN, FIST, PALM, UP])
        self.assertEqual(len(test.sequence), 8)

    def test_waits_for_rest_before_the_beep(self):
        test = AccuracyTest(rest_seconds=2.0)
        beep_time = advance_to_active(test)
        self.assertGreaterEqual(beep_time, 2.0)
        self.assertEqual(test.phase, ACTIVE)

    def test_success_records_the_time(self):
        test = AccuracyTest(trials_per_gesture=1)
        beep = advance_to_active(test)
        test.update(NONE, beep + 0.3)
        test.update(UP, beep + 0.8)
        trial = test.results[0]
        self.assertTrue(trial.success)
        self.assertAlmostEqual(trial.seconds, 0.8)

    def test_timeout_is_a_failure_and_remembers_wrong_gestures(self):
        test = AccuracyTest(trials_per_gesture=1, window_seconds=4.0)
        beep = advance_to_active(test)
        test.update(FIST, beep + 1.0)          # a wrong gesture appears
        test.update(FIST, beep + 1.5)          # the same one again: noted once
        test.update(NONE, beep + 4.1)          # time is over
        trial = test.results[0]
        self.assertFalse(trial.success)
        self.assertIsNone(trial.seconds)
        self.assertEqual(trial.wrong, [FIST])

    def test_old_gesture_must_clear_before_the_next_try(self):
        test = AccuracyTest(trials_per_gesture=1, rest_seconds=0.5, clear_seconds=3.0)
        beep = advance_to_active(test)
        test.update(UP, beep + 0.2)             # try 1 (thumb up) succeeds
        now = beep + 0.2
        beeped = False
        for _ in range(20):                     # the hand is still showing THUMB_UP (the old gesture)
            now += 0.1
            beeped = beeped or test.update(UP, now)
        self.assertFalse(beeped)                # no beep while the old gesture is still there
        test.update(NONE, now + 0.1)
        self.assertEqual(test.phase, ACTIVE)    # it starts as soon as the hand is gone

    def test_gives_up_waiting_for_clear_after_the_limit(self):
        test = AccuracyTest(trials_per_gesture=1, rest_seconds=0.5, clear_seconds=1.0)
        beep = advance_to_active(test)
        test.update(UP, beep + 0.2)
        now, beeped = beep + 0.2, False
        for _ in range(30):
            now += 0.1
            beeped = beeped or test.update(UP, now)
        self.assertTrue(beeped)

    def test_finishes_after_all_tries(self):
        test = AccuracyTest(trials_per_gesture=1)
        now = 0.0
        for gesture in (UP, DOWN, FIST, PALM):
            now = advance_to_active(test, now)
            test.update(gesture, now + 0.5)
            now += 0.5
        self.assertTrue(test.finished)
        self.assertEqual(len(test.results), 4)
        self.assertIsNone(test.target)


class TestDiagnosis(unittest.TestCase):
    def test_classify_frame(self):
        self.assertEqual(classify_frame(FIST, False, False, NONE), "no hand")
        self.assertEqual(classify_frame(FIST, True, False, NONE), "hand moving")
        self.assertEqual(classify_frame(FIST, True, True, FIST), "steady: right gesture")
        self.assertEqual(classify_frame(FIST, True, True, UP), "steady: other gesture")
        self.assertEqual(classify_frame(FIST, True, True, NONE), "steady: unclear")

    def test_failed_try_keeps_where_its_frames_went(self):
        test = AccuracyTest(trials_per_gesture=1, window_seconds=1.0)
        beep = advance_to_active(test)
        for i in range(10):                          # 10 frames of a hand that never stops moving
            test.update(NONE, beep + 0.05 * (i + 1), (True, False, NONE))
        test.update(NONE, beep + 1.1, (True, True, NONE))   # one unclear steady frame, then time is over
        trial = test.results[0]
        self.assertEqual(trial.frames["hand moving"], 10)
        self.assertEqual(trial.frames["steady: unclear"], 1)

    def test_report_explains_failures(self):
        from accuracy_test import Trial
        from collections import Counter
        results = [Trial(FIST, False, None, [], Counter({"hand moving": 3, "no hand": 1}))]
        text = build_report(results)
        self.assertIn("why CLOSED_FIST failed (1 tries)", text)
        self.assertIn("hand moving 75%", text)


class TestTimeline(unittest.TestCase):
    def test_timeline_of_a_successful_try(self):
        test = AccuracyTest(trials_per_gesture=1)
        beep = advance_to_active(test)
        test.update(NONE, beep + 0.2, (False, False, NONE))        # no hand yet
        test.update(NONE, beep + 0.5, (True, False, NONE))         # hand appears, moving
        test.update(NONE, beep + 1.0, (True, True, UP))   # still and right
        test.update(UP, beep + 1.6, (True, True, UP))              # confirmed by the stabilizer
        trial = test.results[0]
        self.assertAlmostEqual(trial.hand_seen, 0.5)
        self.assertAlmostEqual(trial.right_seen, 1.0)
        self.assertAlmostEqual(trial.seconds, 1.6)

    def test_report_splits_the_time(self):
        from accuracy_test import Trial
        results = [Trial(UP, True, 2.0, [], hand_seen=0.5, right_seen=1.5)]
        text = build_report(results)
        self.assertIn("0.50 / 1.00 / 0.50", text)       # your move / filter wait / hold wait


class TestRecorder(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        import os
        import tempfile
        from models.types import HandData
        recorder = Recorder()
        hand = HandData(landmarks=[(0.12345678, 0.5, 0.0)] * 21, aspect_ratio=4 / 3)
        recorder.add(1.23456, "active", UP, hand)
        recorder.add(1.3, "rest", None, None)
        path = os.path.join(tempfile.mkdtemp(), "r.json.gz")
        recorder.save(path, fps=[10.0])
        data = load_recording(path)
        self.assertEqual(len(data["frames"]), 2)
        self.assertEqual(data["frames"][0]["target"], "THUMB_UP")
        self.assertEqual(data["frames"][0]["hand"][0], [0.1235, 0.5])
        self.assertIsNone(data["frames"][1]["hand"])
        self.assertEqual(data["fps"], [10.0])

    def test_run_records_every_frame(self):
        test = AccuracyTest(trials_per_gesture=1)
        recorder = Recorder()

        class Controller:
            def process_frame(self):
                return SimpleNamespace(stable=NONE, frame=None, fps=10.0, hand_found=False, steady=False,
                                       raw=NONE, hand=None)

        calls = []
        run(Controller(), test, show=lambda f, l: calls.append(1) or len(calls) >= 5, beep=lambda: None,
            clock=lambda: 0.0, recorder=recorder)
        self.assertEqual(len(recorder.frames), 5)


class TestIdle(unittest.TestCase):
    def make_controller(self, stables, clock):
        frames = iter(stables)

        class Controller:
            def process_frame(self_inner):
                clock.now += 1.0
                try:
                    stable = next(frames)
                except StopIteration:
                    stable = NONE
                return SimpleNamespace(stable=stable, frame=None, fps=10.0, hand=None)

        return Controller()

    def test_counts_confirmed_gestures_as_false_triggers(self):
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

        clock = Clock()
        controller = self.make_controller([NONE, UP, UP, NONE, FIST, FIST, UP], clock)
        text = run_idle(controller, show=lambda f, l: False, seconds=10, clock=clock)
        self.assertIn("3 gesture(s) confirmed by mistake", text)    # UP, FIST, UP
        self.assertIn("THUMB_UP", text)
        self.assertIn("CLOSED_FIST", text)

    def test_quiet_hand_gives_zero(self):
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

        clock = Clock()
        text = run_idle(self.make_controller([], clock), show=lambda f, l: False, seconds=5, clock=clock)
        self.assertIn("0 gesture(s) confirmed by mistake", text)


class TestReport(unittest.TestCase):
    def test_report_numbers(self):
        from accuracy_test import Trial
        results = [Trial(UP, True, 0.5), Trial(UP, True, 1.5), Trial(UP, False, None, [FIST]),
                   Trial(PALM, True, 1.0)]
        text = build_report(results, fps_values=[10, 20])
        self.assertIn("THUMB_UP", text)
        self.assertIn("67%", text)             # 2 of 3
        self.assertIn("1.00", text)            # average of 0.5 and 1.5
        self.assertIn("CLOSED_FIST", text)     # the wrong gesture is listed
        self.assertIn("OVERALL: 3/4 = 75%", text)
        self.assertIn("15.0", text)            # average FPS


class TestRunLoop(unittest.TestCase):
    def test_loop_runs_until_finished_and_beeps_each_try(self):
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

        clock = Clock()
        test = AccuracyTest(trials_per_gesture=1, rest_seconds=0.2, clear_seconds=0.2)
        beeps = []

        class Controller:
            def process_frame(self_inner):
                clock.now += 0.1
                # the "user" makes the right gesture as soon as the test is active
                stable = test.target if test.phase == ACTIVE else NONE
                return SimpleNamespace(stable=stable, frame=None, fps=15.0, hand_found=True, steady=True, raw=stable, hand=None)

        report = run(Controller(), test, show=lambda frame, lines: False,
                     beep=lambda: beeps.append(1), clock=clock)
        self.assertEqual(len(beeps), 4)
        self.assertIn("OVERALL: 4/4 = 100%", report)

    def test_user_can_stop_early(self):
        test = AccuracyTest(trials_per_gesture=1)

        class Controller:
            def process_frame(self):
                return SimpleNamespace(stable=NONE, frame=None, fps=10.0, hand_found=False, steady=False, raw=NONE)

        calls = []
        run(Controller(), test, show=lambda f, l: calls.append(1) or len(calls) >= 3, beep=lambda: None,
            clock=lambda: 0.0)
        self.assertEqual(len(calls), 3)

    def test_lost_camera_ends_the_loop(self):
        test = AccuracyTest(trials_per_gesture=1)

        class Controller:
            def process_frame(self):
                return None

        run(Controller(), test, show=lambda f, l: False, beep=lambda: None)   # must not hang


if __name__ == "__main__":
    unittest.main()
