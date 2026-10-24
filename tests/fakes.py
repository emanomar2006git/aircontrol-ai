"""Fake parts (camera, detector, audio device, clock) used by the AppController and window tests."""
import numpy as np

from commands.command_mapper import CommandMapper
from commands.media_controller import MediaController
from commands.volume_controller import VolumeController
from core.app_controller import AppController
from models.types import HandData
from tests.test_gesture_recognizer import ALL, CURLED, make_hand


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeCamera:
    """Gives blank frames; every frame takes 0.05 s on the fake clock. Can fail on purpose."""

    def __init__(self, clock, can_open=True, frames=None):
        self.clock = clock
        self.can_open = can_open
        self.frames_left = frames      # None = unlimited
        self.opened = False
        self.released = 0

    def open(self):
        self.opened = self.can_open
        return self.opened

    def read_frame(self):
        if not self.opened or self.frames_left == 0:
            return None
        if self.frames_left is not None:
            self.frames_left -= 1
        self.clock.now += 0.05
        return np.zeros((480, 640, 3), np.uint8)

    def release(self):
        self.opened = False
        self.released += 1


class FakeDetector:
    """Returns hands from a list by frame number; `hand_at(i)` decides. Last value repeats."""

    def __init__(self, hands):
        self.hands = hands            # list of HandData / None
        self.calls = 0
        self.closed = False

    def detect(self, frame):
        hand = self.hands[min(self.calls, len(self.hands) - 1)]
        self.calls += 1
        return hand

    def draw_landmarks(self, frame, hand):
        pass

    def close(self):
        self.closed = True


class FakeAudio:
    def __init__(self, level=0.5):
        self.level = level
        self.fail = False

    def GetMasterVolumeLevelScalar(self):
        if self.fail:
            raise OSError("audio device removed")
        return self.level

    def SetMasterVolumeLevelScalar(self, level, context):
        if self.fail:
            raise OSError("audio device removed")
        self.level = level


def moved(hand, dx, dy):
    return HandData([(x + dx, y + dy, z) for x, y, z in hand.landmarks], hand.aspect_ratio)


PALM = make_hand(ALL, "out")
FIST = make_hand(CURLED, "tucked")
UP = make_hand(CURLED, "up")
DOWN = make_hand(CURLED, "down")


def make_controller(hands, can_open=True, frames=None, detector_factory=None, with_detector=True):
    """Build a real AppController whose camera, detector, audio and media key are fake."""
    clock = Clock()
    audio, keys = FakeAudio(), []
    camera = FakeCamera(clock, can_open, frames)
    detector = FakeDetector(hands) if with_detector else None
    controller = AppController(
        camera=camera, detector=detector, detector_factory=detector_factory,
        mapper=CommandMapper(clock=clock),
        volume=VolumeController(endpoint_factory=lambda: audio),
        media=MediaController(key_press=lambda: keys.append(clock.now), clock=clock),
        clock=clock)
    return controller, camera, detector, audio, keys, clock
