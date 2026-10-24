"""calibrate_gestures.py
Records what the recognizer sees while you do each gesture, and also while you move your hand
WITHOUT making a gesture (relaxed hand). It prints a summary, so we can choose good thresholds.
Run:   python calibrate_gestures.py
Follow the instructions on the video window and KEEP YOUR HAND INSIDE THE PICTURE (see the skeleton).
You will hear a beep at the start of each step. Total time: about 1 minute. At the end, copy ALL the printed result and send it to your mentor.
"""
import math
import time

import cv2

from models.types import GestureType
from recognition.gesture_recognizer import GestureRecognizer
from recognition.motion_filter import MotionFilter
from vision.camera_manager import CameraManager
from vision.hand_detector import HandDetector

FONT = cv2.FONT_HERSHEY_SIMPLEX
GET_READY_SECONDS = 3

# (name, instruction, seconds)
PHASES = [
    ("palm", "OPEN PALM: fingers straight, hold it still", 4),
    ("fist", "CLOSED FIST: close your hand tight, hold it still", 4),
    ("thumb_up", "THUMB UP: fist with the thumb pointing up, hold still", 4),
    ("thumb_down", "THUMB DOWN: fist with the thumb pointing down, hold still", 4),
    ("relaxed_move", "NO GESTURE: RELAXED loose hand, slowly raise it and lower it again and again", 10),
    ("open_close", "NO GESTURE: open and close your hand slowly again and again (hand in place)", 8),
]


def beep(frequency=800, milliseconds=200):
    """A sound that tells you a step has started (Windows only; silent elsewhere)."""
    try:
        import winsound
        winsound.Beep(frequency, milliseconds)
    except Exception:
        pass


def pose_change_speed(previous, hand, dt):
    """How fast the SHAPE of the hand changes: the average movement of all 21 points,
    in hand sizes per second. Large while you open/close the hand or move it, small when it is still."""
    if previous is None or dt <= 0:
        return None
    wx, wy, _ = hand.landmarks[0]
    mx, my, _ = hand.landmarks[9]
    size = math.hypot((wx - mx) * hand.aspect_ratio, wy - my)
    if size == 0:
        return None
    total = 0.0
    for (x1, y1, _), (x2, y2, _) in zip(previous.landmarks, hand.landmarks):
        total += math.hypot((x2 - x1) * hand.aspect_ratio, y2 - y1)
    return total / len(hand.landmarks) / size / dt


def percentile(sorted_values, fraction):
    return sorted_values[min(len(sorted_values) - 1, int(len(sorted_values) * fraction))]


def summarize(records, frames):
    """records: list of (gesture, finger_ratios, thumb_vertical, speed, shape_change), one per frame with a hand."""
    result = {"frames": frames, "found": len(records)}
    if not records:
        return result
    counts = {g.name: 0 for g in GestureType}
    for gesture, *_ in records:
        counts[gesture.name] += 1
    result["percent"] = {name: 100.0 * n / len(records) for name, n in counts.items()}
    loosest = sorted(max(r) for _, r, *_ in records)   # the most "open" finger of each frame
    tightest = sorted(min(r) for _, r, *_ in records)  # the most "closed" finger of each frame
    thumbs = sorted(t for _, _, t, *_ in records)
    speeds = sorted(r[3] for r in records if r[3] is not None)
    changes = sorted(r[4] for r in records if r[4] is not None)
    result["loosest_finger"] = (percentile(loosest, 0.1), percentile(loosest, 0.9))
    result["tightest_finger"] = (percentile(tightest, 0.1), percentile(tightest, 0.9))
    result["thumb"] = (percentile(thumbs, 0.1), percentile(thumbs, 0.9))
    if speeds:
        result["speed"] = (percentile(speeds, 0.5), percentile(speeds, 0.9))
    if changes:
        result["shape_change"] = (percentile(changes, 0.5), percentile(changes, 0.9))
    return result


def run_phase(camera, detector, recognizer, show, clock, instruction, seconds, record=True):
    records, frames = [], 0
    motion = MotionFilter()
    previous_hand, previous_time = None, None
    start = clock()
    while clock() - start < seconds:
        frame = camera.read_frame()
        if frame is None:
            return None
        hand = detector.detect(frame)
        detector.draw_landmarks(frame, hand)
        now = clock()
        frames += 1
        speed = motion.update(hand, now)
        if record and hand is not None:
            info = recognizer.analyze(hand)
            if info is not None:
                change = pose_change_speed(previous_hand, hand, now - previous_time) if previous_hand else None
                records.append((recognizer.recognize(hand), info["finger_ratios"], info["thumb_vertical"],
                                speed, change))
        previous_hand, previous_time = hand, now
        if show(frame, instruction + ("" if hand is not None else "  !!! NO HAND SEEN !!!"),
                seconds - (clock() - start)):
            return None
    return records, frames


def _show_window(frame, text, seconds_left):
    for i, line in enumerate((text[:58], text[58:116], text[116:])):
        if line:
            cv2.putText(frame, line, (10, 28 + 24 * i), FONT, 0.55, (0, 255, 0), 2)
    cv2.putText(frame, f"{seconds_left:0.0f} s", (10, frame.shape[0] - 15), FONT, 0.9, (255, 255, 255), 2)
    if text.endswith("!!!"):
        cv2.putText(frame, "NO HAND SEEN - move your hand into the picture", (10, frame.shape[0] // 2),
                    FONT, 0.7, (0, 0, 255), 2)
    cv2.imshow("AirControl AI - gesture calibration", frame)
    try:
        cv2.setWindowProperty("AirControl AI - gesture calibration", cv2.WND_PROP_TOPMOST, 1)
    except Exception:
        pass
    return (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q"), 27)


def main(camera=None, detector=None, show=_show_window, clock=time.perf_counter, phases=PHASES):
    camera = camera or CameraManager()
    if not camera.open():
        print("ERROR: could not open the camera.")
        return None
    try:
        detector = detector or HandDetector()
    except Exception as error:
        print(f"ERROR: could not start the hand detector: {error}")
        camera.release()
        return None

    recognizer = GestureRecognizer()
    results = {}
    total_frames, total_time = 0, 0.0
    for name, instruction, seconds in phases:
        print(f"\n>>> {instruction}   (starts in {GET_READY_SECONDS} s, lasts {seconds} s)")
        beep(600, 150)
        if run_phase(camera, detector, recognizer, show, clock, "GET READY - " + instruction,
                     GET_READY_SECONDS, record=False) is None:
            break
        beep(1000, 300)
        began = clock()
        outcome = run_phase(camera, detector, recognizer, show, clock, instruction, seconds)
        if outcome is None:
            break
        records, frames = outcome
        results[name] = summarize(records, frames)
        results[name]["fps"] = frames / max(clock() - began, 1e-9)

    detector.close()
    camera.release()
    cv2.destroyAllWindows()
    print_report(results)
    return results


def print_report(results):
    print("\n========== RESULT (copy everything from here) ==========")
    print("percent = how often the recognizer said each gesture (hand found frames only)")
    print("loosest/tightest = finger ratio of the most open / most closed finger, p10..p90")
    print("thumb = thumb vertical, p10..p90")
    print("speed = how much the hand moved/changed in the last 0.3 s (hand sizes), shape = how fast the shape changes per second (median / p90)")
    for name, r in results.items():
        head = f"{name:13}: frames={r['frames']:3} found={r['found']:3} fps={r.get('fps', 0):.0f}"
        if "percent" not in r:
            print(head + "  NO HAND FOUND")
            continue
        p = r["percent"]
        shown = " ".join(f"{k[:9]}={p[k]:.0f}%" for k in p if p[k] >= 1)
        lo, hi = r["loosest_finger"]
        tl, th = r["tightest_finger"]
        a, b = r["thumb"]
        print(head)
        print(f"{'':15}{shown}")
        print(f"{'':15}loosest {lo:.2f}..{hi:.2f}   tightest {tl:.2f}..{th:.2f}   thumb {a:+.2f}..{b:+.2f}")
        sp = r.get("speed")
        sh = r.get("shape_change")
        print(f"{'':15}speed {sp[0]:.2f}/{sp[1]:.2f}   shape {sh[0]:.2f}/{sh[1]:.2f}" if sp and sh else f"{'':15}(not enough frames for speed/shape)")
    print("========================================================")


if __name__ == "__main__":
    main()
