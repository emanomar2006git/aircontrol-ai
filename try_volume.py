"""try_volume.py
Manual test of VolumeController on your real PC. No camera is used.
It changes the volume a little and ALWAYS puts it back to the original value at the end.
Tip: click the speaker icon in the taskbar and watch the slider move while this runs.
"""
import time

from commands.volume_controller import VolumeController

PAUSE = 1.5  # seconds between steps, so you can see/hear the change


def percent(level):
    return "?" if level is None else f"{round(level * 100)}%"


def check(name, ok):
    print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    return ok


def main():
    controller = VolumeController()

    print("1) Reading the volume")
    original = controller.get_volume()
    print(f"   current volume = {percent(original)}")
    if original is None:
        print(f"   ERROR: could not read the volume -> {controller.last_error}")
        return
    results = []

    try:
        print("2) set_volume: move 10% away from the original value")
        target = original - 0.10 if original >= 0.10 else original + 0.10
        controller.set_volume(target)
        time.sleep(PAUSE)
        now = controller.get_volume()
        print(f"   asked for {percent(target)}, read back {percent(now)}")
        results.append(check("volume moved to the requested value",
                             now is not None and abs(now - target) < 0.02))

        print("3) volume_up then volume_down (one step each)")
        before = controller.get_volume()
        up = controller.volume_up()
        time.sleep(PAUSE)
        print(f"   volume_up   : {percent(before)} -> {percent(up)}")
        down = controller.volume_down()
        time.sleep(PAUSE)
        print(f"   volume_down : {percent(up)} -> {percent(down)}")
        results.append(check("volume_up made it louder (unless already 100%)",
                             up is not None and (up > before or before >= 0.99)))
        results.append(check("volume_down made it quieter again",
                             down is not None and up is not None and down < up))
    finally:
        print("4) Putting the volume back")
        controller.set_volume(original)
        time.sleep(0.5)
        restored = controller.get_volume()
        print(f"   original {percent(original)}, now {percent(restored)}")
        results.append(check("original volume restored",
                             restored is not None and abs(restored - original) < 0.02))

    print()
    print("ALL OK" if all(results) else "SOMETHING FAILED - copy this whole output and send it to your mentor.")


if __name__ == "__main__":
    main()
