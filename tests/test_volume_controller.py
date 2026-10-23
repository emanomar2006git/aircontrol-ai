"""Unit tests for VolumeController. A fake audio device is used, so nothing on your PC changes.
Run from the main project folder:  python -m unittest tests.test_volume_controller -v
"""
import unittest

from commands.volume_controller import VolumeController


class FakeEndpoint:
    """Pretends to be the Windows volume control."""

    def __init__(self, level=0.5):
        self.level = level
        self.fail = False

    def GetMasterVolumeLevelScalar(self):
        if self.fail:
            raise OSError("device removed")
        return self.level

    def SetMasterVolumeLevelScalar(self, level, event_context):
        if self.fail:
            raise OSError("device removed")
        self.level = level


def make(level=0.5, step=0.05):
    fake = FakeEndpoint(level)
    return VolumeController(step=step, endpoint_factory=lambda: fake), fake


class TestVolumeController(unittest.TestCase):
    def test_get_volume(self):
        controller, _ = make(0.30)
        self.assertAlmostEqual(controller.get_volume(), 0.30)

    def test_volume_up_and_down_by_step(self):
        controller, fake = make(0.50)
        self.assertAlmostEqual(controller.volume_up(), 0.55)
        self.assertAlmostEqual(fake.level, 0.55)
        self.assertAlmostEqual(controller.volume_down(), 0.50)

    def test_custom_step(self):
        controller, _ = make(0.50, step=0.10)
        self.assertAlmostEqual(controller.volume_up(), 0.60)

    def test_never_above_one(self):
        controller, fake = make(0.98)
        self.assertEqual(controller.volume_up(), 1.0)
        self.assertEqual(controller.volume_up(), 1.0)
        self.assertEqual(fake.level, 1.0)

    def test_never_below_zero(self):
        controller, fake = make(0.02)
        self.assertEqual(controller.volume_down(), 0.0)
        self.assertEqual(controller.volume_down(), 0.0)
        self.assertEqual(fake.level, 0.0)

    def test_set_volume_is_limited(self):
        controller, fake = make()
        self.assertEqual(controller.set_volume(5), 1.0)
        self.assertEqual(controller.set_volume(-3), 0.0)
        self.assertEqual(fake.level, 0.0)

    def test_no_audio_device_does_not_crash(self):
        def no_device():
            raise RuntimeError("no audio device")
        controller = VolumeController(endpoint_factory=no_device)
        self.assertIsNone(controller.get_volume())
        self.assertIsNone(controller.volume_up())
        self.assertIsNone(controller.set_volume(0.5))
        self.assertIn("no audio device", controller.last_error)

    def test_pycaw_missing_does_not_crash(self):
        def missing():
            raise ImportError("No module named 'pycaw'")
        controller = VolumeController(endpoint_factory=missing)
        self.assertIsNone(controller.volume_down())
        self.assertIn("ImportError", controller.last_error)

    def test_error_while_working_then_recovers(self):
        controller, fake = make(0.50)
        self.assertAlmostEqual(controller.get_volume(), 0.50)
        fake.fail = True
        self.assertIsNone(controller.volume_up())
        self.assertIsNotNone(controller.last_error)
        fake.fail = False
        self.assertAlmostEqual(controller.volume_up(), 0.55)
        self.assertIsNone(controller.last_error)


if __name__ == "__main__":
    unittest.main()
