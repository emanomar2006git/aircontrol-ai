"""try_hand.py
Manual test: live camera + hand detection.
Draws the hand skeleton and shows FPS. Press 'q' in the video window to quit.
"""
import time

import cv2

from vision.camera_manager import CameraManager
from vision.hand_detector import HandDetector


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

    print("Hand detection started. Click the video window and press 'q' to quit.")
    previous_time = time.perf_counter()

    while True:
        frame = camera.read_frame()
        if frame is None:
            print("ERROR: lost the camera.")
            break

        hand = detector.detect(frame)
        detector.draw_landmarks(frame, hand)

        now = time.perf_counter()
        fps = 1.0 / (now - previous_time) if now > previous_time else 0.0
        previous_time = now
        status = "Hand: found" if hand else "Hand: not found"
        cv2.putText(frame, f"FPS: {fps:.0f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, status, (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("AirControl AI - hand detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.close()
    camera.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
