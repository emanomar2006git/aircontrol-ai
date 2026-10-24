"""GestureStabilizer: removes flicker from the raw gesture of each frame."""
from models.types import GestureType

DEFAULT_REQUIRED_FRAMES = 5  # about 0.2 - 0.3 seconds at 17 - 30 FPS

# How many frames each gesture must be held. Play / Pause need a longer hold than the volume,
# because a wrong play/pause is more annoying than a wrong volume step.
# Reason for holding longer: while you open or close your hand, it passes through shapes that look like
# another gesture (for example THUMB_DOWN) for a moment. A longer hold ignores that short moment.
GESTURE_HOLD = {
    GestureType.THUMB_UP: 8,
    GestureType.THUMB_DOWN: 8,
    GestureType.CLOSED_FIST: 10,
    GestureType.OPEN_PALM: 10,
}
VOLUME_HOLD = GESTURE_HOLD  # old name, kept so older scripts still work


class GestureStabilizer:
    """Changes its output only after a NEW gesture was seen in N frames in a row.

    Why: the recognizer works on every single frame, so one bad frame can give a wrong
    answer for a moment (flicker). A volume or play/pause command must not be triggered by that.

    Example with required_frames=3:
        raw frames :  NONE  UP    UP    UP    DOWN  UP    UP    UP
        stable     :  NONE  NONE  NONE  UP    UP    UP    UP    UP
    The single DOWN frame was ignored, and UP appeared only after 3 UP frames in a row.
    """

    def __init__(self, required_frames=DEFAULT_REQUIRED_FRAMES, per_gesture=None):
        """required_frames: frames in a row needed to accept a new gesture.
        per_gesture: optional dictionary {GestureType: frames} for gestures that need a different number."""
        per_gesture = per_gesture or {}
        if required_frames < 1 or any(n < 1 for n in per_gesture.values()):
            raise ValueError("the number of frames must be at least 1")
        self.required_frames = required_frames
        self.per_gesture = dict(per_gesture)
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

        needed = self.per_gesture.get(self._candidate, self.required_frames)
        if self._count >= needed:
            self._stable = self._candidate
            self._count = 0
        return self._stable
