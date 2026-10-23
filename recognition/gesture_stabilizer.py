"""GestureStabilizer: removes flicker from the raw gesture of each frame."""
from models.types import GestureType

DEFAULT_REQUIRED_FRAMES = 5  # about 0.2 - 0.3 seconds at 17 - 30 FPS


class GestureStabilizer:
    """Changes its output only after a NEW gesture was seen in N frames in a row.

    Why: the recognizer works on every single frame, so one bad frame can give a wrong
    answer for a moment (flicker). A volume or play/pause command must not be triggered by that.

    Example with required_frames=3:
        raw frames :  NONE  UP    UP    UP    DOWN  UP    UP    UP
        stable     :  NONE  NONE  NONE  UP    UP    UP    UP    UP
    The single DOWN frame was ignored, and UP appeared only after 3 UP frames in a row.
    """

    def __init__(self, required_frames=DEFAULT_REQUIRED_FRAMES):
        if required_frames < 1:
            raise ValueError("required_frames must be at least 1")
        self.required_frames = required_frames
        self.reset()

    def reset(self):
        """Forget everything and start again from GestureType.NONE."""
        self._stable = GestureType.NONE
        self._candidate = GestureType.NONE
        self._count = 0

    @property
    def stable(self):
        """The current stable gesture."""
        return self._stable

    def update(self, raw_gesture):
        """Give the raw gesture of the newest frame. Returns the stable gesture."""
        if raw_gesture == self._stable:
            # We are still on the stable gesture: any earlier doubt is cancelled.
            self._candidate = self._stable
            self._count = 0
            return self._stable

        if raw_gesture == self._candidate:
            self._count += 1
        else:
            self._candidate = raw_gesture
            self._count = 1

        if self._count >= self.required_frames:
            self._stable = self._candidate
            self._count = 0
        return self._stable
