"""Unit tests for MediaController. No key is really pressed: a fake key press is used.
Run from the main project folder:  python -m unittest tests.test_media_controller -v
"""
import unittest

from commands.media_controller import MediaController
from models.types import Command


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeKey:
    def __init__(self):
        self.presses = 0
        self.fail = False

    def __call__(self):
        if self.fail:
            raise RuntimeError("keyboard blocked")
        self.presses += 1


def make(min_interval=1.0):
    key, clock = FakeKey(), FakeClock()
    return MediaController(key_press=key, clock=clock, min_interval=min_interval), key, clock


class TestMediaController(unittest.TestCase):
    def test_starts_unknown(self):
        media, key, _ = make()
        self.assertIsNone(media.is_playing)
        self.assertEqual(key.presses, 0)

    def test_first_pause_is_sent_when_state_unknown(self):
        media, key, _ = make()
        self.assertTrue(media.pause())
        self.assertEqual(key.presses, 1)
        self.assertIs(media.is_playing, False)

    def test_first_play_is_sent_when_state_unknown(self):
        media, key, _ = make()
        self.assertTrue(media.play())
        self.assertIs(media.is_playing, True)

    def test_pause_twice_sends_only_one_key(self):
        media, key, clock = make()
        media.pause()
        clock.advance(5)
        self.assertFalse(media.pause())
        self.assertEqual(key.presses, 1)

    def test_play_twice_sends_only_one_key(self):
        media, key, clock = make()
        media.play()
        clock.advance(5)
        self.assertFalse(media.play())
        self.assertEqual(key.presses, 1)

    def test_pause_then_play_then_pause(self):
        media, key, clock = make()
        for action, expected in [(media.pause, False), (media.play, True), (media.pause, False)]:
            self.assertTrue(action())
            self.assertIs(media.is_playing, expected)
            clock.advance(2)
        self.assertEqual(key.presses, 3)

    def test_cooldown_blocks_a_quick_second_press(self):
        media, key, clock = make(min_interval=1.0)
        media.pause()
        clock.advance(0.5)
        self.assertFalse(media.play())          # too soon
        self.assertIs(media.is_playing, False)  # state unchanged
        self.assertEqual(key.presses, 1)
        clock.advance(0.6)
        self.assertTrue(media.play())           # now it is allowed
        self.assertEqual(key.presses, 2)

    def test_key_failure_does_not_crash_and_keeps_state(self):
        media, key, _ = make()
        key.fail = True
        self.assertFalse(media.pause())
        self.assertIn("keyboard blocked", media.last_error)
        self.assertIsNone(media.is_playing)
        key.fail = False
        self.assertTrue(media.pause())
        self.assertIsNone(media.last_error)

    def test_execute(self):
        media, key, clock = make()
        self.assertFalse(media.execute(Command.NONE))
        self.assertFalse(media.execute(Command.VOLUME_UP))
        self.assertEqual(key.presses, 0)
        self.assertTrue(media.execute(Command.PAUSE))
        clock.advance(2)
        self.assertTrue(media.execute(Command.PLAY))
        self.assertEqual(key.presses, 2)

    def test_reset_state(self):
        media, key, clock = make()
        media.pause()
        clock.advance(2)
        media.reset_state()
        self.assertIsNone(media.is_playing)
        self.assertTrue(media.pause())  # sent again, because the state is unknown


if __name__ == "__main__":
    unittest.main()
