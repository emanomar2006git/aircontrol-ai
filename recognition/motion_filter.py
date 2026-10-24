"""MotionFilter: tells whether the hand is STILL, so gestures are accepted only from a still hand."""
import math
from collections import deque

WRIST = 0
MIDDLE_MCP = 9

DEFAULT_MAX_CHANGE = 0.08    # hand sizes. The hand is "still" if nothing moved more than this ...
DEFAULT_WINDOW_SECONDS = 0.3  # ... during the last 0.3 seconds.


class MotionFilter:
    """Measures how much the hand changed (moved AND changed shape) during the last 0.3 seconds.

    The number is: the average movement of the 21 landmark points, in "hand sizes"
    (hand size = wrist to middle knuckle, so it does not depend on the distance to the camera).
    We take the biggest change between the newest frame and any frame of the last 0.3 seconds.
    It does not depend on the FPS, because it uses a fixed time window.

    Why: when you raise your hand, or close/open it, it passes through shapes that look like a gesture
    (for example a half-closed hand with the thumb out looks like THUMB_DOWN). A gesture must come
    from a hand that is still, so while the hand changes we ignore the gestures.

    Use:  change = motion.update(hand, now)   then check  motion.steady
    """

    def __init__(self, max_change=DEFAULT_MAX_CHANGE, window_seconds=DEFAULT_WINDOW_SECONDS):
        self.max_change = max_change
        self.window_seconds = window_seconds
        self.reset()

    def reset(self):
        self._history = deque()   # (time, points) of the last frames
        self.change = None

    @property
    def steady(self):
        """True when the hand was still during the whole last window."""
        return self.change is not None and self.change < self.max_change

    @staticmethod
    def _points(hand):
        """The landmarks as (x, y) in image heights, and the hand size, or None if not measurable."""
        wx, wy, _ = hand.landmarks[WRIST]
        mx, my, _ = hand.landmarks[MIDDLE_MCP]
        size = math.hypot((wx - mx) * hand.aspect_ratio, wy - my)
        if size == 0:
            return None
        return [(x * hand.aspect_ratio, y) for x, y, _ in hand.landmarks], size

    def update(self, hand, now):
        """Give the hand of the newest frame (or None) and the time in seconds.
        Returns the change in hand sizes, or None when it cannot be known yet
        (no hand, or the hand appeared less than 0.3 seconds ago)."""
        measured = self._points(hand) if hand is not None else None
        if measured is None:  # no hand: forget everything
            self.reset()
            return None

        points, size = measured
        self._history.append((now, points))
        # keep only the frames of the window (plus the newest frame)
        while len(self._history) > 1 and now - self._history[0][0] > self.window_seconds * 1.5:
            self._history.popleft()

        oldest_time = self._history[0][0]
        if now - oldest_time < self.window_seconds * 0.8:  # not enough history yet
            self.change = None
            return None

        biggest = 0.0
        for time_before, before in self._history:
            if now - time_before > self.window_seconds:
                continue
            total = sum(math.hypot(x1 - x2, y1 - y2) for (x1, y1), (x2, y2) in zip(before, points))
            biggest = max(biggest, total / len(points) / size)
        self.change = biggest
        return self.change
