"""CommandMapper: turns the stable gesture of each frame into a Command."""
import time

from models.types import Command, GestureType

DEFAULT_REPEAT_INTERVAL = 0.3  # seconds between two volume steps while the gesture is held

# gesture -> (command, repeat)
#   repeat=True : the command is sent again and again while you keep the gesture (volume)
#   repeat=False: the command is sent once, when the gesture appears (play / pause)
# To add or change a gesture, you only change this dictionary.
GESTURE_TABLE = {
    GestureType.THUMB_UP: (Command.VOLUME_UP, True),
    GestureType.THUMB_DOWN: (Command.VOLUME_DOWN, True),
    GestureType.CLOSED_FIST: (Command.PAUSE, False),
    GestureType.OPEN_PALM: (Command.PLAY, False),
}


class CommandMapper:
    """Call map() once per frame with the STABLE gesture. It returns a Command.

    Most frames return Command.NONE (nothing to do). A real command is returned
    - once, when a gesture appears, and
    - for repeating gestures, again every repeat_interval seconds while it is held.
    This is the cooldown of FR-12: it stops commands from firing on every single frame.
    """

    def __init__(self, repeat_interval=DEFAULT_REPEAT_INTERVAL, clock=None, table=None):
        self.repeat_interval = repeat_interval
        self._clock = clock or time.monotonic
        self._table = GESTURE_TABLE if table is None else table
        self.reset()

    def reset(self):
        self._last_gesture = GestureType.NONE
        self._last_time = 0.0

    def map(self, gesture):
        now = self._clock()
        entry = self._table.get(gesture)

        if gesture != self._last_gesture:  # a new gesture just appeared
            self._last_gesture = gesture
            if entry is None:
                return Command.NONE
            self._last_time = now
            return entry[0]

        if entry is not None and entry[1] and now - self._last_time >= self.repeat_interval:
            self._last_time = now  # same gesture still held: repeat
            return entry[0]
        return Command.NONE
