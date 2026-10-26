"""accuracy_test.py
Tests the whole app with your real hand: for each gesture it asks you to make it several times
and measures (1) how often it is recognized, (2) how many seconds it takes, (3) wrong gestures.
Commands are NOT executed (control stays disabled), so your volume and videos are safe.

Run:  python accuracy_test.py            (default 8 tries per gesture, about 5 minutes)
      python accuracy_test.py --trials 5
      python accuracy_test.py --idle           (60 s of natural movement: counts FALSE triggers)
Both save a recording of your hand (.json.gz) so the settings can be tuned on real data.
Click on the video window. Each try: relax / lower your hand -> a beep -> make the gesture shown.
Press ESC to stop early.
"""
import gzip
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

from models.types import GestureType

ORDER = [GestureType.THUMB_UP, GestureType.THUMB_DOWN, GestureType.CLOSED_FIST, GestureType.OPEN_PALM]
LABELS = {
    GestureType.THUMB_UP: "THUMB UP (fist with thumb pointing up)",
    GestureType.THUMB_DOWN: "THUMB DOWN (fist with thumb pointing down)",
    GestureType.CLOSED_FIST: "CLOSED FIST",
    GestureType.OPEN_PALM: "OPEN PALM (all fingers open)",
}
REST, WAIT_CLEAR, ACTIVE, FINISHED = "rest", "wait_clear", "active", "finished"


@dataclass
class Trial:
    target: GestureType
    success: bool
    seconds: float            # time from the beep until the gesture was confirmed (None if it never was)
    wrong: list = field(default_factory=list)   # other gestures that were confirmed during this try
    frames: Counter = field(default_factory=Counter)   # where the frames of this try went (see classify_frame)
    hand_seen: float = None      # seconds after the beep when the camera first saw a hand
    right_seen: float = None     # seconds after the beep when the hand was still and showed the right gesture


FRAME_KINDS = ["no hand", "hand moving", "steady: right gesture", "steady: other gesture", "steady: unclear"]


def classify_frame(target, hand_found, steady, raw):
    """Say where one frame went. This tells WHY a try failed:
    no hand      = the camera did not see a hand
    hand moving  = the motion filter ignored the frame (the hand was not still)
    steady: right gesture / other gesture = the recognizer said the target / another gesture
    steady: unclear = the hand was still but the recognizer said NONE (fingers half bent)
    """
    if not hand_found:
        return FRAME_KINDS[0]
    if not steady:
        return FRAME_KINDS[1]
    if raw == target:
        return FRAME_KINDS[2]
    if raw == GestureType.NONE:
        return FRAME_KINDS[4]
    return FRAME_KINDS[3]


class AccuracyTest:
    """The state machine of the test. It knows nothing about the camera or the window."""

    def __init__(self, trials_per_gesture=8, rest_seconds=2.5, window_seconds=4.0, clear_seconds=3.0):
        self.sequence = ORDER * trials_per_gesture       # thumb up, down, fist, palm, thumb up, ...
        self.rest_seconds = rest_seconds
        self.window_seconds = window_seconds
        self.clear_seconds = clear_seconds
        self.results = []
        self.phase = REST
        self._phase_start = None
        self._seen = []
        self._frames = Counter()
        self._hand_seen = None
        self._right_seen = None

    @property
    def target(self):
        return self.sequence[len(self.results)] if self.phase != FINISHED else None

    @property
    def finished(self):
        return self.phase == FINISHED

    @property
    def trial_number(self):
        return min(len(self.results) + 1, len(self.sequence))

    def update(self, stable, now, frame_info=None):
        """Give the stable gesture of the newest frame. Returns True when a beep should sound.

        frame_info = (hand_found, steady, raw) of the same frame; it is only used for the diagnosis.
        """
        if self.phase == FINISHED:
            return False
        if self._phase_start is None:
            self._phase_start = now
        if self.phase == REST:
            if now - self._phase_start >= self.rest_seconds:
                self._change(WAIT_CLEAR, now)
        elif self.phase == WAIT_CLEAR:
            # the previous gesture must be gone first, otherwise the old one would count
            if stable == GestureType.NONE or now - self._phase_start >= self.clear_seconds:
                self._seen = []
                self._frames = Counter()
                self._hand_seen = self._right_seen = None
                self._change(ACTIVE, now)
                return True
        elif self.phase == ACTIVE:
            if frame_info is not None:
                kind = classify_frame(self.target, *frame_info)
                self._frames[kind] += 1
                elapsed = now - self._phase_start
                if frame_info[0] and self._hand_seen is None:
                    self._hand_seen = elapsed
                if kind == FRAME_KINDS[2] and self._right_seen is None:
                    self._right_seen = elapsed
            if stable == self.target:
                self._finish(True, now - self._phase_start, now)
            else:
                if stable != GestureType.NONE and stable not in self._seen:
                    self._seen.append(stable)
                if now - self._phase_start >= self.window_seconds:
                    self._finish(False, None, now)
        return False

    def _change(self, phase, now):
        self.phase = phase
        self._phase_start = now

    def _finish(self, success, seconds, now):
        self.results.append(Trial(self.target, success, seconds, list(self._seen), Counter(self._frames),
                                    self._hand_seen, self._right_seen))
        if len(self.results) >= len(self.sequence):
            self.phase = FINISHED
        else:
            self._change(REST, now)


class Recorder:
    """Saves every frame (time, phase, hand landmarks) so the settings can be tuned later on the SAME data."""

    def __init__(self):
        self.frames = []

    def add(self, now, phase, target, hand):
        points = None if hand is None else [[round(x, 4), round(y, 4)] for x, y, _z in hand.landmarks]
        self.frames.append({"t": round(now, 3), "phase": phase, "target": target.name if target else "",
                            "hand": points, "aspect": round(hand.aspect_ratio, 4) if hand else None})

    def save(self, path, **extra):
        with gzip.open(path, "wt", encoding="utf-8") as file:
            json.dump({"frames": self.frames, **extra}, file)


def load_recording(path):
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return json.load(file)


def build_report(results, fps_values=()):
    """A text table of the results: success rate, time to recognize, wrong gestures."""
    lines = ["gesture        tries  ok   rate   avg s  max s  wrong gestures seen"]
    total_ok = total = 0
    for gesture in ORDER:
        mine = [r for r in results if r.target == gesture]
        if not mine:
            continue
        ok = [r for r in mine if r.success]
        times = [r.seconds for r in ok]
        wrong = sorted({w.name for r in mine for w in r.wrong})
        avg = f"{sum(times) / len(times):5.2f}" if times else "    -"
        top = f"{max(times):5.2f}" if times else "    -"
        lines.append(f"{gesture.name:14} {len(mine):4}  {len(ok):3}  {100 * len(ok) / len(mine):4.0f}%  "
                     f"{avg}  {top}  {', '.join(wrong) if wrong else '-'}")
        total_ok += len(ok)
        total += len(mine)
    if total:
        lines.append(f"OVERALL: {total_ok}/{total} = {100 * total_ok / total:.0f}%")
    lines.append("")
    lines.append("where the time goes (successful tries, average seconds after the beep):")
    lines.append("gesture        hand seen   still+right pose   confirmed   -> your move / filter wait / hold wait")
    for gesture in ORDER:
        good = [r for r in results if r.target == gesture and r.success and r.hand_seen is not None
                and r.right_seen is not None]
        if good:
            a = sum(r.hand_seen for r in good) / len(good)
            b = sum(r.right_seen for r in good) / len(good)
            c = sum(r.seconds for r in good) / len(good)
            lines.append(f"{gesture.name:14} {a:8.2f}   {b:14.2f}   {c:9.2f}   -> "
                         f"{a:.2f} / {b - a:.2f} / {c - b:.2f}")
    for gesture in ORDER:
        failed = [r for r in results if r.target == gesture and not r.success]
        counts = Counter()
        for r in failed:
            counts.update(r.frames)
        total_frames = sum(counts.values())
        if failed and total_frames:
            parts = [f"{kind} {100 * counts[kind] / total_frames:.0f}%" for kind in FRAME_KINDS if counts[kind]]
            lines.append(f"why {gesture.name} failed ({len(failed)} tries): " + ", ".join(parts))
    fps_values = [f for f in fps_values if f]
    if fps_values:
        lines.append(f"average FPS during the test: {sum(fps_values) / len(fps_values):.1f}")
    return "\n".join(lines)


def run(controller, test, show, beep, clock=time.perf_counter, recorder=None):
    """The loop. `show(frame, text_lines)` shows the picture and returns True if the user wants to stop."""
    fps_values = []
    while not test.finished:
        result = controller.process_frame()
        if result is None:
            print("ERROR: lost the camera.")
            break
        fps_values.append(result.fps)
        if recorder is not None:
            recorder.add(clock(), test.phase, test.target, result.hand)
        if test.update(result.stable, clock(), (result.hand_found, result.steady, result.raw)):
            beep()
        if show(result.frame, describe(test, result)):
            break
    return build_report(test.results, fps_values)


IDLE_HELP = ("Move your hand NATURALLY: raise it, lower it, relax it, scratch your face, wave, reach for the mouse. "
             "Do NOT try to make any gesture.")


def run_idle(controller, show, seconds=60.0, clock=time.perf_counter, recorder=None):
    """Natural-movement test: every gesture the program CONFIRMS here is a false trigger."""
    start = clock()
    mistakes = []
    previous = GestureType.NONE
    fps_values = []
    while clock() - start < seconds:
        result = controller.process_frame()
        if result is None:
            print("ERROR: lost the camera.")
            break
        now = clock() - start
        fps_values.append(result.fps)
        if recorder is not None:
            recorder.add(clock(), "idle", None, result.hand)
        if result.stable != previous and result.stable != GestureType.NONE:
            mistakes.append((now, result.stable))
        previous = result.stable
        if show(result.frame, ["DO NOT MAKE GESTURES! Just move your hand naturally",
                               "(scratch face, reach for the mouse, wave, relax it)",
                               f"time left: {max(0, seconds - now):.0f} s   confirmed by mistake: {len(mistakes)}"]):
            break
    lines = [f"natural movement for {min(clock() - start, seconds):.0f} s: "
             f"{len(mistakes)} gesture(s) confirmed by mistake (false triggers)"]
    lines += [f"   at {when:5.1f} s: {gesture.name}" for when, gesture in mistakes]
    fps_values = [f for f in fps_values if f]
    if fps_values:
        lines.append(f"average FPS: {sum(fps_values) / len(fps_values):.1f}")
    return "\n".join(lines)


def describe(test, result):
    """The text lines drawn on the video."""
    head = f"Try {test.trial_number}/{len(test.sequence)}"
    if test.finished:
        return ["Done! Look at the terminal."]
    if test.phase == ACTIVE:
        return [f"{head}  MAKE NOW:", LABELS[test.target], f"seen: {result.stable.name}"]
    if test.phase == WAIT_CLEAR:
        return [head, "Lower your hand...", f"seen: {result.stable.name}"]
    return [head, "Rest. Next: " + LABELS[test.target], f"seen: {result.stable.name}"]


def main():
    import cv2

    from core.app_controller import AppController

    controller = AppController()      # control stays disabled: nothing is executed
    if not controller.start():
        print(controller.message)
        return

    def beep():
        try:
            import winsound
            winsound.Beep(880, 150)
        except Exception:
            print("\a", end="")

    def show(frame, lines):
        for i, text in enumerate(lines):
            color = (0, 255, 0) if i == 0 else (255, 255, 255)
            cv2.putText(frame, text, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow("AirControl AI - accuracy test", frame)
        return (cv2.waitKey(1) & 0xFF) == 27

    recorder = Recorder()
    if "--idle" in sys.argv:
        print("Natural movement test (60 s). Click on the video window. ESC = stop.")
        print(IDLE_HELP)
        report = run_idle(controller, show, recorder=recorder)
        path = "idle_recording.json.gz"
    else:
        trials = 8
        if "--trials" in sys.argv:
            trials = int(sys.argv[sys.argv.index("--trials") + 1])
        print(f"Accuracy test: {trials} tries per gesture. Click on the video window. ESC = stop.")
        test = AccuracyTest(trials_per_gesture=trials)
        report = run(controller, test, show, beep, recorder=recorder)
        path = "accuracy_recording.json.gz"
    controller.stop()
    cv2.destroyAllWindows()
    recorder.save(path)
    print("\n========== RESULT (copy everything from here) ==========")
    print(report)
    print("========================================================")
    print(f"Saved the recording of your hand: {path}  (attach this file in the chat)")


if __name__ == "__main__":
    main()
