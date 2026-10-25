"""try_camera_modes.py
Tests a few camera settings and prints the real FPS of each (camera only, 3 seconds each).
Run:  python try_camera_modes.py        (stay in front of the camera, with as much light as you can)
"""
import platform
import time

import cv2

SECONDS = 3.0
# (name, fourcc or None, width, height, ask for 30 FPS?)
MODES = [
    ("default settings", None, None, None, False),
    ("ask 30 FPS", None, None, None, True),
    ("MJPG 640x480", "MJPG", 640, 480, True),
    ("MJPG 1280x720", "MJPG", 1280, 720, True),
    ("YUY2 640x480", "YUY2", 640, 480, True),
]


def open_camera(fourcc, width, height, want_fps):
    backend = getattr(cv2, "CAP_DSHOW", 0) if platform.system() == "Windows" else 0
    capture = cv2.VideoCapture(0, backend)
    if not capture.isOpened():
        return None
    if fourcc:
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    if width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if want_fps:
        capture.set(cv2.CAP_PROP_FPS, 30)
    return capture


def measure_fps(capture, seconds=SECONDS):
    for _ in range(5):          # skip the first frames (the camera is still starting)
        capture.read()
    frames = 0
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        ok, _frame = capture.read()
        if not ok:
            return None
        frames += 1
    return frames / (time.perf_counter() - start)


def main():
    print("Testing camera modes, about 3 seconds each...\n")
    for name, fourcc, width, height, want_fps in MODES:
        capture = open_camera(fourcc, width, height, want_fps)
        if capture is None:
            print(f"{name:18}: could not open the camera")
            continue
        fps = measure_fps(capture)
        size = f"{int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        capture.release()
        time.sleep(0.5)
        result = "no frames" if fps is None else f"{fps:5.1f} FPS"
        print(f"{name:18}: {result}   (real size {size})")
    print("\nDone. Send me these lines.")


if __name__ == "__main__":
    main()
