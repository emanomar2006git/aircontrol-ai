"""Tests for MainWindow. They need a screen: if there is none, they are skipped.
Run:  python -m unittest tests.test_main_window -v
"""
import unittest

try:
    import tkinter as tk
except ImportError:      # Python without Tkinter
    tk = None

from tests.fakes import FIST, PALM, UP, make_controller

if tk is not None:
    from ui.main_window import MainWindow


def make_root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


@unittest.skipIf(tk is None, "Tkinter is not available")
class TestMainWindow(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        if self.root is None:
            self.skipTest("no screen available")
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def build(self, hands, **kwargs):
        controller, camera, detector, audio, keys, clock = make_controller(hands, **kwargs)
        window = MainWindow(controller, root=self.root)
        return window, controller, audio, keys

    def test_first_look(self):
        window, controller, *_ = self.build([PALM])
        window._refresh_texts()
        self.assertEqual(window.control_label.cget("text"), "CONTROL: DISABLED")
        self.assertIn("Enable", window.toggle_button.cget("text"))
        self.assertEqual(window.video_state_label.cget("text"), "Video (believed): UNKNOWN")

    def test_toggle_button_enables_and_disables(self):
        window, controller, *_ = self.build([PALM])
        window.toggle_button.invoke()
        self.assertTrue(controller.enabled)
        self.assertEqual(window.control_label.cget("text"), "CONTROL: ENABLED")
        self.assertIn("Disable", window.toggle_button.cget("text"))
        window.toggle_button.invoke()
        self.assertFalse(controller.enabled)
        self.assertEqual(window.control_label.cget("text"), "CONTROL: DISABLED")

    def test_space_key_toggles(self):
        window, controller, *_ = self.build([PALM])
        self.root.deiconify()
        self.root.update()
        self.root.focus_force()
        self.root.update()
        self.root.event_generate("<space>")
        self.root.update()
        self.assertTrue(controller.enabled)

    def test_frames_are_shown_and_texts_follow_the_state(self):
        window, controller, *_ = self.build([UP])
        controller.start()
        controller.set_enabled(True)
        for _ in range(40):
            window._tick()
            self.root.update_idletasks()
            window._after_id = None          # we call _tick ourselves, so forget the scheduled one
        self.assertNotEqual(window.video_label.cget("image"), "")
        self.assertEqual(window.gesture_label.cget("text"), "Gesture: THUMB_UP")
        self.assertEqual(window.command_label.cget("text"), "Last command: VOLUME_UP")
        self.assertIn("Hand: still", window.hand_label.cget("text"))
        self.assertGreater(float(window.volume_bar.cget("value")), 55)
        self.assertTrue(window.volume_label.cget("text").startswith("Volume: "))
        self.assertTrue(window.fps_label.cget("text").startswith("FPS: "))

    def test_the_picture_area_has_the_full_size(self):
        """A bug we had: the picture area was only a few pixels wide.
        We check the size the layout ASKS for (reqwidth), which does not depend on when Windows draws the window."""
        window, controller, *_ = self.build([UP])
        controller.start()
        for _ in range(4):
            window._tick()
            window._after_id = None
        self.root.update_idletasks()
        picture_area = window.video_label.master
        self.assertGreaterEqual(picture_area.winfo_reqwidth(), 640)
        self.assertGreaterEqual(picture_area.winfo_reqheight(), 480)
        self.assertGreaterEqual(self.root.winfo_reqwidth(), 640 + 250)   # picture + the side panel

    def test_video_state_buttons(self):
        window, controller, *_ = self.build([FIST])
        window.set_video_state(True)
        self.assertEqual(window.video_state_label.cget("text"), "Video (believed): PLAYING")
        window.set_video_state(False)
        self.assertEqual(window.video_state_label.cget("text"), "Video (believed): PAUSED")
        window.set_video_state(None)
        self.assertEqual(window.video_state_label.cget("text"), "Video (believed): UNKNOWN")

    def test_camera_not_available_then_retry(self):
        controller, camera, detector, audio, keys, clock = make_controller([PALM], can_open=False)
        window = MainWindow(controller, root=self.root)
        self.assertFalse(controller.start())
        window._refresh_texts()
        self.assertIn("Camera not available", window.status_label.cget("text"))
        self.assertNotIn("disabled", window.retry_button.state())
        camera.can_open = True
        window.retry_button.invoke()
        self.assertTrue(controller.running)
        self.assertIn("disabled", window.retry_button.state())     # nothing to retry while running

    def test_camera_lost_shows_message(self):
        window, controller, *_ = self.build([PALM], frames=3)
        controller.start()
        for _ in range(6):
            window._tick()
            window._after_id = None
        self.assertEqual(window.video_label.cget("text"), "Camera is off")
        self.assertIn("Camera lost", window.status_label.cget("text"))

    def test_close_stops_everything_once(self):
        window, controller, *_ = self.build([PALM])
        controller.start()
        window.close()
        window.close()                       # a second call must do nothing
        self.assertFalse(controller.running)
        self.assertTrue(window._closed)


@unittest.skipIf(tk is None, "Tkinter is not available")
class TestRealLoop(unittest.TestCase):
    """A bug we had (Phase 10): a loop with no waiting kept Tk so busy that the window was never shown,
    although the camera was running. This test runs the REAL loop (window.run) and looks at the window."""

    def test_window_is_shown_while_the_real_loop_runs(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no screen available")
        controller = make_controller([PALM] * 100000)[0]
        window = MainWindow(controller, root=root)
        state = {}

        def look():
            state["mapped"] = root.winfo_ismapped()
            state["picture_width"] = window.video_label.winfo_width()
            window.close()

        root.after(1500, look)
        window.run()
        self.assertTrue(state["mapped"], "the window was never shown")
        self.assertGreaterEqual(state["picture_width"], 600)


if __name__ == "__main__":
    unittest.main()