"""measure_ui_speed.py
Runs the REAL window for a few seconds and measures where the time of each loop goes:
camera, hand detection, the rest of the processing, drawing the picture, updating texts,
and "waiting" (time spent inside Tkinter between two loops).
Keep your hand in front of the camera.   Run:  python measure_ui_speed.py
"""
import time

SECONDS = 8.0


class Timer:
    """Wraps methods of an object and adds up the time they take."""

    def __init__(self, clock=time.perf_counter):
        self.clock = clock
        self.totals = {}
        self.calls = {}

    def wrap(self, obj, method_name, label):
        original = getattr(obj, method_name)

        def timed(*args, **kwargs):
            start = self.clock()
            try:
                return original(*args, **kwargs)
            finally:
                self.totals[label] = self.totals.get(label, 0.0) + (self.clock() - start)
                self.calls[label] = self.calls.get(label, 0) + 1

        setattr(obj, method_name, timed)


def report(timer, total_seconds):
    loops = timer.calls.get("process", 0)
    if loops == 0:
        return "No frames were processed (is the camera free?)."
    per_loop = {label: 1000.0 * value / loops for label, value in timer.totals.items()}
    process = per_loop.get("process", 0.0)
    camera = per_loop.get("camera", 0.0)
    detect = per_loop.get("detect", 0.0)
    other = max(0.0, process - camera - detect)
    show = per_loop.get("show", 0.0)
    texts = per_loop.get("texts", 0.0)
    loop_ms = 1000.0 * total_seconds / loops
    waiting = max(0.0, loop_ms - process - show - texts)
    lines = [
        f"FPS of the window loop : {loops / total_seconds:.1f}   ({loops} loops, {loop_ms:.0f} ms per loop)",
        f"  camera read          : {camera:5.1f} ms",
        f"  hand detection       : {detect:5.1f} ms",
        f"  other processing     : {other:5.1f} ms   (gestures, filters, volume check)",
        f"  drawing the picture  : {show:5.1f} ms   (average per loop, it is drawn every 2nd frame)",
        f"  updating the texts   : {texts:5.1f} ms",
        f"  waiting inside Tk    : {waiting:5.1f} ms",
    ]
    return "\n".join(lines)


def run(controller=None, seconds=SECONDS, root=None):
    """Open the window, run it for `seconds`, and return the report text."""
    from ui.main_window import MainWindow
    if controller is None:
        from core.app_controller import AppController
        controller = AppController()
    window = MainWindow(controller, root=root)
    timer = Timer()
    timer.wrap(controller, "process_frame", "process")
    timer.wrap(window, "_show_frame", "show")
    timer.wrap(window, "_refresh_texts", "texts")
    timer.wrap(controller.camera, "read_frame", "camera")

    original_start = controller.start
    clock = {}

    def start_and_wrap_detector():
        ok = original_start()           # opening the camera and the model can take several seconds
        if controller.detector is not None:
            timer.wrap(controller.detector, "detect", "detect")
        clock["started"] = time.perf_counter()                   # the measuring time starts only now
        window.root.after(int(seconds * 1000), window.close)
        return ok

    controller.start = start_and_wrap_detector
    window.run()
    return report(timer, time.perf_counter() - clock.get("started", time.perf_counter()))


def main():
    print(f"Opening the window for {SECONDS:.0f} seconds. Keep your hand in front of the camera...")
    print(run())
    print("Done. Send me these lines.")


if __name__ == "__main__":
    main()
