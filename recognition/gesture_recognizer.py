"""GestureRecognizer: rule-based gesture recognition from hand landmarks."""
import math

from models.types import GestureType

# Landmark numbers of the MediaPipe hand model.
WRIST = 0
THUMB_MCP = 2          # base joint of the thumb
THUMB_TIP = 4          # tip of the thumb
MIDDLE_MCP = 9         # base joint of the middle finger (used to measure the hand size)
# (middle joint, tip) of the index, middle, ring and little finger.
FINGERS = [(6, 8), (10, 12), (14, 16), (18, 20)]

# Values you can tune after testing with a real hand.
EXTENDED_RATIO = 1.15      # a finger is "extended" if its tip is this much farther from the wrist than its middle joint
CURLED_RATIO = 1.0         # a finger is "curled" if its tip is closer to the wrist than its middle joint
THUMB_VERTICAL_MIN = 0.35  # how far the thumb must point up (or down), measured in hand sizes


class GestureRecognizer:
    """Looks at the 21 landmarks of one hand and decides which gesture it shows."""

    def __init__(self, extended_ratio=EXTENDED_RATIO, curled_ratio=CURLED_RATIO,
                 thumb_vertical_min=THUMB_VERTICAL_MIN):
        self.extended_ratio = extended_ratio
        self.curled_ratio = curled_ratio
        self.thumb_vertical_min = thumb_vertical_min

    @staticmethod
    def _distance(hand, a, b):
        """Distance between landmark a and landmark b, measured in image heights."""
        ax, ay, _ = hand.landmarks[a]
        bx, by, _ = hand.landmarks[b]
        # x is a fraction of the (wider) image width, so we scale it by the aspect ratio
        return math.hypot((ax - bx) * hand.aspect_ratio, ay - by)

    def analyze(self, hand):
        """Return the raw numbers the rules are based on, or None if they cannot be measured.

        finger_ratios: for each finger, (wrist to tip) divided by (wrist to middle joint).
                       Big number = finger straight. Small number = finger folded.
        thumb_vertical: how far the thumb points up (positive) or down (negative),
                        in hand sizes.
        """
        hand_size = self._distance(hand, WRIST, MIDDLE_MCP)
        if hand_size == 0:
            return None

        ratios = []
        for middle_joint, tip in FINGERS:
            to_joint = self._distance(hand, WRIST, middle_joint)
            to_tip = self._distance(hand, WRIST, tip)
            ratios.append(to_tip / to_joint if to_joint > 0 else 0.0)

        thumb_base_y = hand.landmarks[THUMB_MCP][1]
        thumb_tip_y = hand.landmarks[THUMB_TIP][1]
        thumb_vertical = (thumb_base_y - thumb_tip_y) / hand_size  # y grows downward in images
        return {"finger_ratios": ratios, "thumb_vertical": thumb_vertical}

    def recognize(self, hand):
        """Return the GestureType shown by the hand (GestureType.NONE if unclear or no hand)."""
        if hand is None:
            return GestureType.NONE
        info = self.analyze(hand)
        if info is None:
            return GestureType.NONE

        ratios = info["finger_ratios"]
        extended = sum(1 for r in ratios if r > self.extended_ratio)
        curled = sum(1 for r in ratios if r < self.curled_ratio)
        thumb = info["thumb_vertical"]

        if extended == 4:
            return GestureType.OPEN_PALM
        if curled == 4:
            if thumb > self.thumb_vertical_min:
                return GestureType.THUMB_UP
            if thumb < -self.thumb_vertical_min:
                return GestureType.THUMB_DOWN
            return GestureType.CLOSED_FIST
        return GestureType.NONE
