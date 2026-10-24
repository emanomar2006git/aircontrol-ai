"""Unit tests for CommandMapper. A fake clock is used, so the tests need no waiting.
Run from the main project folder:  python -m unittest tests.test_command_mapper -v
"""
import unittest

from commands.command_mapper import CommandMapper
from models.types import Command, GestureType

UP = GestureType.THUMB_UP
DOWN = GestureType.THUMB_DOWN
FIST = GestureType.CLOSED_FIST
PALM = GestureType.OPEN_PALM
NONE = GestureType.NONE


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make(interval=0.3):
    clock = FakeClock()
    return CommandMapper(repeat_interval=interval, clock=clock), clock


class TestCommandMapper(unittest.TestCase):
    def test_no_gesture_gives_none(self):
        mapper, clock = make()
        for _ in range(5):
            self.assertEqual(mapper.map(NONE), Command.NONE)
            clock.advance(1)

    def test_all_four_gestures_map_to_their_command(self):
        for gesture, command in [(UP, Command.VOLUME_UP), (DOWN, Command.VOLUME_DOWN),
                                 (FIST, Command.PAUSE), (PALM, Command.PLAY)]:
            with self.subTest(gesture=gesture.name):
                mapper, _ = make()
                self.assertEqual(mapper.map(gesture), command)

    def test_volume_repeats_while_held(self):
        mapper, clock = make(0.25)
        results = []
        for _ in range(8):             # 8 frames, 0.125 s apart (these numbers are exact in binary)
            results.append(mapper.map(UP))
            clock.advance(0.125)
        V, N = Command.VOLUME_UP, Command.NONE
        # a volume step at 0.0 s, 0.25 s, 0.5 s and 0.75 s
        self.assertEqual(results, [V, N, V, N, V, N, V, N])

    def test_play_pause_fire_only_once_while_held(self):
        for gesture, command in [(FIST, Command.PAUSE), (PALM, Command.PLAY)]:
            with self.subTest(gesture=gesture.name):
                mapper, clock = make()
                self.assertEqual(mapper.map(gesture), command)
                for _ in range(20):
                    clock.advance(1)
                    self.assertEqual(mapper.map(gesture), Command.NONE)

    def test_releasing_and_showing_again_fires_again(self):
        mapper, clock = make()
        self.assertEqual(mapper.map(FIST), Command.PAUSE)
        self.assertEqual(mapper.map(NONE), Command.NONE)
        self.assertEqual(mapper.map(FIST), Command.PAUSE)

    def test_changing_gesture_fires_the_new_command_at_once(self):
        mapper, clock = make()
        self.assertEqual(mapper.map(UP), Command.VOLUME_UP)
        clock.advance(0.05)
        self.assertEqual(mapper.map(DOWN), Command.VOLUME_DOWN)

    def test_custom_table(self):
        table = {GestureType.OPEN_PALM: (Command.VOLUME_UP, False)}
        mapper = CommandMapper(clock=FakeClock(), table=table)
        self.assertEqual(mapper.map(PALM), Command.VOLUME_UP)
        self.assertEqual(mapper.map(UP), Command.NONE)

    def test_reset(self):
        mapper, clock = make()
        mapper.map(FIST)
        mapper.reset()
        self.assertEqual(mapper.map(FIST), Command.PAUSE)


if __name__ == "__main__":
    unittest.main()
