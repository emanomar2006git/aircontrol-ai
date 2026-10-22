"""try_camera.py
Manual test for CameraManager: shows the live camera with an FPS counter.
Press 'q' in the video window to quit.
"""
import time

import cv2

from vision.camera_manager import CameraManager


def main():
    camera = CameraManager()
    if not camera.open():
        print("ERROR: could not open the camera. Close other apps that use it and try again.")
        return

    print("Camera started. Click the video window and press 'q' to quit.")
    previous_time = time.perf_counter()

    while True:
        frame = camera.read_frame()
        if frame is None:
            print("ERROR: lost the camera.")
            break

        now = time.perf_counter()
        fps = 1.0 / (now - previous_time) if now > previous_time else 0.0
        previous_time = now
        cv2.putText(frame, f"FPS: {fps:.0f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("AirControl AI - camera test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
    print("Camera released. Done.")


if __name__ == "__main__":
    main()
