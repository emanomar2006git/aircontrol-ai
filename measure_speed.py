"""measure_speed.py
Finds WHERE the time goes in one frame, to explain a low FPS.
  Part 1: camera only            -> is the camera itself slow? (dark room = slow camera)
  Part 2: camera + hand detector -> is the hand detection slow?
Keep your hand in front of the camera during part 2, then repeat once with NO hand.
Run:  python measure_speed.py            (each part takes about 5 seconds)
"""
import sys
import time

import cv2

SECONDS = 5.0


def measure(read_frame, detect=None, seconds=SECONDS, clock=time.perf_counter):
    """Run the loop for `seconds` and return the average time of each stage in milliseconds."""
    times = {"camera": 0.0, "detect": 0.0, "draw+encode": 0.0}
    frames = 0
    start = clock()
    while clock() - start < seconds:
        t0 = clock()
        frame = read_frame()
        t1 = clock()
        if frame is None:
            return None
        hand = detect(frame) if detect else None
        t2 = clock()
        cv2.imencode(".ppm", frame)  # the cost of showing the frame in the window
        t3 = clock()
        times["camera"] += t1 - t0
        times["detect"] += t2 - t1
        times["draw+encode"] += t3 - t2
        frames += 1
    total = clock() - start
    result = {name: 1000.0 * value / frames for name, value in times.items()}
    result["fps"] = frames / total
    result["frames"] = frames
    return result


def show(title, result):
    if result is None:
        print(f"{title}: ERROR - no frame from the camera")
        return
    print(f"{title}")
    print(f"   FPS            : {result['fps']:.1f}   ({result['frames']} frames)")
    print(f"   camera read    : {result['camera']:.1f} ms per frame")
    print(f"   hand detection : {result['detect']:.1f} ms per frame")
    print(f"   draw + encode  : {result['draw+encode']:.1f} ms per frame")


def main():
    from vision.camera_manager import CameraManager
    camera = CameraManager()
    if not camera.open():
        print("ERROR: could not open the camera. Close other apps that use it.")
        return
    print("Part 1 of 2: camera only (5 s). Hand not needed.")
    show("CAMERA ONLY", measure(camera.read_frame))

    try:
        from vision.hand_detector import HandDetector
        detector = HandDetector()
    except Exception as error:
        print(f"ERROR: hand detector: {error}")
        camera.release()
        return
    input("\nPart 2 of 2: put your hand in front of the camera, then press Enter...")
    show("CAMERA + HAND DETECTION", measure(camera.read_frame, detector.detect))
    detector.close()
    camera.release()


if __name__ == "__main__":
    sys.exit(main())
