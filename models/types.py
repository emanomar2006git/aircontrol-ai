"""Shared data types: HandData, GestureType, Command."""
from dataclasses import dataclass
from enum import Enum


@dataclass
class HandData:
    """One detected hand.

    landmarks is a list of 21 points. Each point is a tuple (x, y, z).
    x and y are between 0 and 1 (a fraction of the image width and height).
    """
    landmarks: list


class GestureType(Enum):
    """The gestures the system can recognize."""
    THUMB_UP = "thumb_up"
    THUMB_DOWN = "thumb_down"
    CLOSED_FIST = "closed_fist"
    OPEN_PALM = "open_palm"
    NONE = "none"


class Command(Enum):
    """The commands the system can execute."""
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    PLAY = "play"
    PAUSE = "pause"
    NONE = "none"
