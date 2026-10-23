"""Unit tests for GestureRecognizer.

There is no camera here: we build a fake hand from numbers (see make_hand) and check
that the recognizer gives the right answer.
Run from the main project folder:  python -m unittest tests.test_gesture_recognizer -v
"""
import math
import unittest

from models.types import GestureType, HandData
from recognition.gesture_recognizer import GestureRecognizer

PALM_SIZE = 0.25  # the hand is 25% of the image height (wrist to middle knuckle)

# Base joint of each finger: index, middle, ring, little. Wrist is (0, 0), "up" is negative y.
# All numbers are in "palm units" (1.0 = wrist to middle knuckle).
FINGER_BASES = [(-0.30, -1.00), (-0.10, -1.02), (0.10, -0.97), (0.28, -0.85)]
FINGER_LENGTHS = [(0.42, 0.25, 0.20), (0.46, 0.28, 0.21), (0.42, 0.26, 0.20), (0.33, 0.19, 0.17)]

# Thumb joints: (CMC, MCP, IP, TIP)
THUMBS = {
    "out":    [(-0.22, -0.25), (-0.45, -0.50), (-0.62, -0.70), (-0.75, -0.88)],  # open hand
    "tucked": [(-0.22, -0.25), (-0.40, -0.50), (-0.25, -0.60), (-0.08, -0.62)],  # inside a fist
    "up":     [(-0.25, -0.25), (-0.45, -0.55), (-0.45, -0.80), (-0.45, -1.05)],
    "down":   [(-0.25, -0.25), (-0.45, -0.40), (-0.45, -0.15), (-0.45, 0.10)],
}


def finger_joints(base, lengths, state):
    """Return the 4 joints (base, middle, upper, tip) of one finger in a given state."""
    x, y = base
    l1, l2, l3 = lengths
    if state == "extended":
        pip, dip, tip = y - l1, y - l1 - l2, y - l1 - l2 - l3
    elif state == "curled":
        pip = y - 0.15
        dip = pip + 0.12
        tip = dip + 0.14
    else:  # "half": bent a little, not clearly straight and not clearly folded
        pip = y - 0.8 * l1
        dip = pip - 0.10
        tip = dip
    return [(x, y), (x, pip), (x, dip), (x, tip)]


def make_hand(fingers, thumb, rotation_deg=0, aspect_ratio=4 / 3):
    """Build a HandData from 4 finger states ('extended', 'curled', 'half') and a thumb pose."""
    points = [(0.0, 0.0)] + THUMBS[thumb]
    for base, lengths, state in zip(FINGER_BASES, FINGER_LENGTHS, fingers):
        points += finger_joints(base, lengths, state)

    angle = math.radians(rotation_deg)
    landmarks = []
    for x, y in points:
        rx = x * math.cos(angle) - y * math.sin(angle)  # turn the whole hand
        ry = x * math.sin(angle) + y * math.cos(angle)
        px = 0.5 * aspect_ratio + rx * PALM_SIZE        # place it near the centre of the image
        py = 0.6 + ry * PALM_SIZE
        landmarks.append((px / aspect_ratio, py, 0.0))  # x and y as a fraction of width / height
    return HandData(landmarks=landmarks, aspect_ratio=aspect_ratio)


ALL = ["extended"] * 4
CURLED = ["curled"] * 4


class TestGestureRecognizer(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer()

    def test_open_palm(self):
        self.assertEqual(self.recognizer.recognize(make_hand(ALL, "out")), GestureType.OPEN_PALM)

    def test_open_palm_in_any_rotation(self):
        for angle in (0, 45, 90, 135, 180, 270):
            with self.subTest(angle=angle):
                hand = make_hand(ALL, "out", rotation_deg=angle)
                self.assertEqual(self.recognizer.recognize(hand), GestureType.OPEN_PALM)

    def test_closed_fist(self):
        self.assertEqual(self.recognizer.recognize(make_hand(CURLED, "tucked")), GestureType.CLOSED_FIST)

    def test_thumb_up(self):
        self.assertEqual(self.recognizer.recognize(make_hand(CURLED, "up")), GestureType.THUMB_UP)

    def test_thumb_down(self):
        self.assertEqual(self.recognizer.recognize(make_hand(CURLED, "down")), GestureType.THUMB_DOWN)

    def test_half_bent_fingers_give_none(self):
        self.assertEqual(self.recognizer.recognize(make_hand(["half"] * 4, "tucked")), GestureType.NONE)

    def test_three_fingers_give_none(self):
        fingers = ["extended", "extended", "extended", "curled"]
        self.assertEqual(self.recognizer.recognize(make_hand(fingers, "out")), GestureType.NONE)

    def test_no_hand_gives_none(self):
        self.assertEqual(self.recognizer.recognize(None), GestureType.NONE)

    def test_same_result_on_square_and_wide_images(self):
        cases = [(ALL, "out", GestureType.OPEN_PALM),
                 (CURLED, "tucked", GestureType.CLOSED_FIST),
                 (CURLED, "up", GestureType.THUMB_UP),
                 (CURLED, "down", GestureType.THUMB_DOWN)]
        for aspect in (1.0, 4 / 3, 16 / 9):
            for fingers, thumb, expected in cases:
                with self.subTest(aspect=aspect, expected=expected.name):
                    hand = make_hand(fingers, thumb, aspect_ratio=aspect)
                    self.assertEqual(self.recognizer.recognize(hand), expected)

    def test_analyze_numbers(self):
        extended = self.recognizer.analyze(make_hand(ALL, "out"))
        curled = self.recognizer.analyze(make_hand(CURLED, "tucked"))
        self.assertTrue(all(r > 1.15 for r in extended["finger_ratios"]))
        self.assertTrue(all(r < 1.0 for r in curled["finger_ratios"]))

    def test_broken_hand_with_zero_size(self):
        flat = HandData(landmarks=[(0.5, 0.5, 0.0)] * 21)
        self.assertEqual(self.recognizer.recognize(flat), GestureType.NONE)


if __name__ == "__main__":
    unittest.main()
