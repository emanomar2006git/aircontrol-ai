"""Tests for AppController with fake parts (no camera, no screen, no sound).
Run:  python -m unittest tests.test_app_controller -v
"""
import unittest

from models.types import Command, GestureType
from tests.fakes import DOWN, FIST, PALM, UP, make_controller, moved


def run_frames(controller, count):
    last = None
    for _ in range(count):
        result = controller.process_frame()
        if result is not None:
            last = result
    return last


class TestStart(unittest.TestCase):
    def test_camera_not_available(self):
        controller, camera, *_ = make_controller([None], can_open=False)
        self.assertFalse(controller.start())
        self.assertFalse(controller.running)
        self.assertIn("Camera not available", controller.message)
        self.assertIsNone(controller.process_frame())

    def test_detector_fails_to_start(self):
        def broken():
            raise FileNotFoundError("hand_landmarker.task")
        controller, camera, *_ = make_controller([None], detector_factory=broken, with_detector=False)
        self.assertFalse(controller.start())
        self.assertIn("download_model.py", controller.message)
        self.assertIn("hand_landmarker.task", controller.message)
        self.assertEqual(camera.released, 1)      # the camera is not kept open

    def test_start_reads_the_volume(self):
        controller, *_ = make_controller([None])
        self.assertTrue(controller.start())
        self.assertAlmostEqual(controller.volume_level, 0.5)
        self.assertTrue(controller.running)

    def test_start_without_volume_device_still_works(self):
        controller, _, _, audio, *_ = make_controller([None])
        audio.fail = True
        self.assertTrue(controller.start())
        self.assertIsNone(controller.volume_level)
        self.assertIn("Volume is not available", controller.message)

    def test_stop_is_safe_to_repeat(self):
        controller, camera, detector, *_ = make_controller([None])
        controller.start()
        controller.stop()
        controller.stop()
        self.assertFalse(controller.running)
        self.assertTrue(detector.closed)
        self.assertGreaterEqual(camera.released, 1)


class TestGestures(unittest.TestCase):
    def test_disabled_by_default_nothing_changes(self):
        controller, _, _, audio, keys, _ = make_controller([UP])
        controller.start()
        self.assertFalse(controller.enabled)
        run_frames(controller, 40)
        self.assertEqual(audio.level, 0.5)
        self.assertEqual(controller.last_command, Command.VOLUME_UP)   # still shown, but not executed

    def test_thumb_up_raises_the_volume(self):
        controller, _, _, audio, *_ = make_controller([UP])
        controller.start()
        controller.set_enabled(True)
        result = run_frames(controller, 40)
        self.assertGreater(audio.level, 0.6)
        self.assertEqual(result.stable, GestureType.THUMB_UP)
        self.assertAlmostEqual(controller.volume_level, audio.level)

    def test_thumb_down_lowers_the_volume(self):
        controller, _, _, audio, *_ = make_controller([DOWN])
        controller.start()
        controller.set_enabled(True)
        run_frames(controller, 40)
        self.assertLess(audio.level, 0.4)

    def test_moving_hand_is_ignored(self):
        hands = [moved(PALM, 0, -0.012 * i) for i in range(40)]
        controller, _, _, audio, keys, _ = make_controller(hands)
        controller.start()
        controller.set_video_state(False)
        controller.set_enabled(True)
        result = run_frames(controller, 40)
        self.assertEqual(keys, [])
        self.assertFalse(result.steady)
        self.assertEqual(result.raw, GestureType.NONE)

    def test_fist_pauses_a_playing_video_once(self):
        controller, _, _, _, keys, _ = make_controller([FIST])
        controller.start()
        controller.set_video_state(True)
        controller.set_enabled(True)
        run_frames(controller, 60)
        self.assertEqual(len(keys), 1)
        self.assertIs(controller.video_state, False)

    def test_fist_does_nothing_when_the_video_is_already_paused(self):
        controller, _, _, _, keys, _ = make_controller([FIST])
        controller.start()
        controller.set_video_state(False)
        controller.set_enabled(True)
        run_frames(controller, 60)
        self.assertEqual(keys, [])
        self.assertIn("ignored", controller.message)

    def test_palm_plays_a_paused_video(self):
        controller, _, _, _, keys, _ = make_controller([PALM])
        controller.start()
        controller.set_video_state(False)
        controller.set_enabled(True)
        run_frames(controller, 60)
        self.assertEqual(len(keys), 1)
        self.assertIs(controller.video_state, True)

    def test_pause_gesture_held_while_disabled_does_not_fire_when_enabled(self):
        controller, _, _, _, keys, _ = make_controller([FIST])
        controller.start()
        controller.set_video_state(True)
        run_frames(controller, 30)           # fist held, control disabled: the PAUSE command is consumed
        controller.set_enabled(True)
        run_frames(controller, 10)
        self.assertEqual(keys, [])           # it fires only after you show the gesture again

    def test_volume_gesture_held_while_enabling_continues_to_repeat(self):
        controller, _, _, audio, *_ = make_controller([UP])
        controller.start()
        run_frames(controller, 30)
        controller.set_enabled(True)
        run_frames(controller, 10)           # the next repeat of the volume step is executed
        self.assertGreater(audio.level, 0.5)

    def test_volume_error_is_reported_not_raised(self):
        controller, _, _, audio, *_ = make_controller([UP])
        controller.start()
        controller.set_enabled(True)
        audio.fail = True
        run_frames(controller, 40)
        self.assertIn("Volume error", controller.message)
        self.assertTrue(controller.running)

    def test_detector_error_does_not_crash(self):
        controller, _, detector, *_ = make_controller([PALM])
        controller.start()
        detector.detect = lambda frame: (_ for _ in ()).throw(RuntimeError("model crashed"))
        result = controller.process_frame()
        self.assertFalse(result.hand_found)
        self.assertIn("model crashed", controller.message)


class TestCameraLost(unittest.TestCase):
    def test_camera_lost_stops_cleanly(self):
        controller, camera, detector, *_ = make_controller([PALM], frames=5)
        controller.start()
        run_frames(controller, 5)
        self.assertIsNone(controller.process_frame())
        self.assertFalse(controller.running)
        self.assertIn("Camera lost", controller.message)
        self.assertTrue(detector.closed)

    def test_retry_after_the_camera_comes_back(self):
        controller, camera, *_ = make_controller([PALM], can_open=False)
        self.assertFalse(controller.start())
        camera.can_open = True
        self.assertTrue(controller.start())
        self.assertIsNotNone(controller.process_frame())


class TestStatus(unittest.TestCase):
    def test_fps_is_about_20_with_a_50_ms_frame(self):
        controller, *_ = make_controller([PALM])
        controller.start()
        result = run_frames(controller, 30)
        self.assertAlmostEqual(result.fps, 20, delta=1)

    def test_volume_changed_by_another_app_is_shown(self):
        controller, _, _, audio, *_ = make_controller([PALM])
        controller.start()
        audio.level = 0.9
        run_frames(controller, 30)           # 1.5 s on the fake clock
        self.assertAlmostEqual(controller.volume_level, 0.9)

    def test_set_enabled_message(self):
        controller, *_ = make_controller([PALM])
        controller.set_enabled(True)
        self.assertTrue(controller.enabled)
        self.assertEqual(controller.message, "Control enabled.")


if __name__ == "__main__":
    unittest.main()
