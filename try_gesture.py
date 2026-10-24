"""try_gesture.py
Manual test: live camera + hand detection + gesture recognition + stabilizer.
Shows the raw gesture (every frame), the stable gesture (after the stabilizer) and the numbers.
Press 'q' in the video window to quit.
"""
import time

import cv2

from recognition.gesture_recognizer import (
    CURLED_RATIO, EXTENDED_RATIO, THUMB_VERTICAL_MIN, GestureRecognizer)
from recognition.gesture_stabilizer import GESTURE_HOLD, GestureStabilizer
from recognition.motion_filter import MotionFilter
from models.types import GestureType
from vision.camera_manager import CameraManager
from vision.hand_detector import HandDetector

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 255, 0)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)


def draw_overlay(frame, raw, stable, info, speed, steady, fps):
    """Write the stable gesture, the raw gesture, the finger numbers and the FPS on the frame."""
    cv2.putText(frame, f"Stable: {stable.name}", (10, 35), FONT, 1.0, GREEN, 2)
    cv2.putText(frame, f"Raw: {raw.name}", (10, 125), FONT, 0.6, WHITE, 2)
    change_text = "-" if speed is None else f"{speed:.2f}"
    cv2.putText(frame, f"Hand change: {change_text}  ({'STILL' if steady else 'MOVING - ignored'})",
                (10, 150), FONT, 0.6, GREEN if steady else (0, 0, 255), 2)
    if info is not None:
        r = info["finger_ratios"]
        cv2.putText(frame, f"I {r[0]:.2f}  M {r[1]:.2f}  R {r[2]:.2f}  P {r[3]:.2f}",
                    (10, 70), FONT, 0.6, YELLOW, 2)
        cv2.putText(frame, f"Thumb vertical: {info['thumb_vertical']:+.2f}",
                    (10, 95), FONT, 0.6, YELLOW, 2)
    cv2.putText(frame, f"FPS: {fps:.0f}", (10, frame.shape[0] - 15), FONT, 0.7, WHITE, 2)


def main():
    camera = CameraManager()
    if not camera.open():
        print("ERROR: could not open the camera. Close other apps that use it and try again.")
        return

    try:
        detector = HandDetector()
    except Exception as error:
        print(f"ERROR: could not start the hand detector: {error}")
        print("Did you run  python download_model.py  first?")
        camera.release()
        return

    recognizer = GestureRecognizer()
    stabilizer = GestureStabilizer(per_gesture=GESTURE_HOLD)
    motion = MotionFilter()
    print("Gesture recognition started. Click the video window and press 'q' to quit.")
    print(f"I M R P = the 4 fingers.  extended if > {EXTENDED_RATIO},  curled if < {CURLED_RATIO}")
    print(f"Thumb vertical: thumb up if > {THUMB_VERTICAL_MIN},  thumb down if < -{THUMB_VERTICAL_MIN}")
    previous_time = time.perf_counter()

    while True:
        frame = camera.read_frame()
        if frame is None:
            print("ERROR: lost the camera.")
            break

        hand = detector.detect(frame)
        detector.draw_landmarks(frame, hand)
        now = time.perf_counter()
        speed = motion.update(hand, now)
        raw = recognizer.recognize(hand) if motion.steady else GestureType.NONE
        stable = stabilizer.update(raw)
        info = recognizer.analyze(hand) if hand else None

        fps = 1.0 / (now - previous_time) if now > previous_time else 0.0
        previous_time = now
        draw_overlay(frame, raw, stable, info, speed, motion.steady, fps)

        cv2.imshow("AirControl AI - gesture recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.close()
    camera.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
