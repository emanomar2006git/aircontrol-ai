"""HandDetector: finds the hand and its 21 landmarks (MediaPipe)."""
import time
from pathlib import Path

import cv2
import mediapipe as mp

from models.types import HandData

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "assets" / "hand_landmarker.task"

# Pairs of landmark numbers joined by a line (the "bones" of the hand skeleton).
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index finger
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle finger
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring finger
    (13, 17), (17, 18), (18, 19), (19, 20),  # little finger
    (0, 17),                                 # edge of the palm
]


class HandDetector:
    """Finds one hand in a camera frame and returns its 21 landmarks."""

    def __init__(self, model_path=DEFAULT_MODEL_PATH, max_hands=1, min_confidence=0.5):
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._start_time = time.perf_counter()
        self._last_timestamp_ms = -1

    def _next_timestamp_ms(self):
        """VIDEO mode needs a timestamp (in ms) that always increases."""
        timestamp = int((time.perf_counter() - self._start_time) * 1000)
        if timestamp <= self._last_timestamp_ms:
            timestamp = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp
        return timestamp

    def detect(self, frame):
        """Look for a hand in a camera frame. Returns HandData, or None if no hand is visible."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # OpenCV is BGR, MediaPipe wants RGB
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(image, self._next_timestamp_ms())

        if not result.hand_landmarks:
            return None
        points = result.hand_landmarks[0]
        height, width = frame.shape[:2]
        return HandData(landmarks=[(p.x, p.y, p.z) for p in points],
                        aspect_ratio=width / height)

    def draw_landmarks(self, frame, hand):
        """Draw the hand skeleton on the frame. Does nothing if hand is None."""
        if hand is None:
            return
        height, width = frame.shape[:2]
        points = [(int(x * width), int(y * height)) for x, y, _ in hand.landmarks]
        for start, end in HAND_CONNECTIONS:
            cv2.line(frame, points[start], points[end], (0, 255, 0), 2)
        for point in points:
            cv2.circle(frame, point, 4, (0, 0, 255), -1)

    def close(self):
        """Free the MediaPipe resources."""
        self._landmarker.close()
