"""Tests for CameraManager settings (a fake capture object, no camera needed).
Run:  python -m unittest tests.test_camera_manager -v
"""
import unittest
from unittest import mock

import cv2

from vision.camera_manager import CameraManager


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.settings = {}

    def isOpened(self):
        return self.opened

    def set(self, prop, value):
        self.settings[prop] = value
        return True

    def release(self):
        self.opened = False


class TestCameraSettings(unittest.TestCase):
    def open_with(self, fake, **kwargs):
        with mock.patch("vision.camera_manager.cv2.VideoCapture", return_value=fake):
            manager = CameraManager(**kwargs)
            return manager, manager.open()

    def test_asks_for_the_fast_mode(self):
        fake = FakeCapture()
        _manager, ok = self.open_with(fake)
        self.assertTrue(ok)
        self.assertEqual(fake.settings[cv2.CAP_PROP_FRAME_WIDTH], 640)
        self.assertEqual(fake.settings[cv2.CAP_PROP_FRAME_HEIGHT], 480)
        self.assertEqual(fake.settings[cv2.CAP_PROP_FPS], 30)
        self.assertEqual(fake.settings[cv2.CAP_PROP_FOURCC], cv2.VideoWriter_fourcc(*"YUY2"))

    def test_settings_can_be_turned_off(self):
        fake = FakeCapture()
        self.open_with(fake, width=None, height=None, fourcc=None, fps=None)
        self.assertEqual(fake.settings, {})

    def test_failed_open_returns_false(self):
        fake = FakeCapture(opened=False)
        _manager, ok = self.open_with(fake)
        self.assertFalse(ok)
        self.assertEqual(fake.settings, {})


if __name__ == "__main__":
    unittest.main()
