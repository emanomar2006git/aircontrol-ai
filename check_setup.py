"""check_setup.py
Checks that this computer is ready to build AirControl AI.

Usage:
    python check_setup.py            (checks Python and the libraries)
    python check_setup.py --camera   (also tries to read one frame from the camera)

It only READS information. It never changes the volume or presses any key.
"""
import platform
import struct
import sys
from importlib.metadata import PackageNotFoundError, version

results = []  # True / False for every real check (skipped checks are not counted)


def report(name, ok, detail=""):
    """Print one line like:  [OK]   name - detail"""
    mark = "[OK]  " if ok else "[FAIL]"
    print(f"{mark} {name}" + (f" - {detail}" if detail else ""))
    results.append(ok)


def skip(name, reason):
    print(f"[SKIP] {name} - {reason}")


def package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown version"


def check_python():
    v = sys.version_info
    bits = struct.calcsize("P") * 8
    ok = (v.major, v.minor) >= (3, 10) and bits == 64
    detail = f"{v.major}.{v.minor}.{v.micro}, {bits}-bit"
    if not ok:
        detail += "  (need Python 3.10+ and 64-bit; 3.12 is recommended)"
    report("Python", ok, detail)


def check_opencv():
    try:
        import cv2
        report("OpenCV (cv2)", True, f"version {cv2.__version__}")
    except Exception as e:
        report("OpenCV (cv2)", False, f"{type(e).__name__}: {e}")


def check_numpy():
    try:
        import numpy
        report("NumPy", True, f"version {numpy.__version__}")
    except Exception as e:
        report("NumPy", False, f"{type(e).__name__}: {e}")


def check_mediapipe():
    try:
        import mediapipe as mp
        has_landmarker = hasattr(mp.tasks.vision, "HandLandmarker")
        detail = f"version {package_version('mediapipe')}"
        if not has_landmarker:
            detail += "  (HandLandmarker not found - reinstall mediapipe)"
        report("MediaPipe (Tasks API: HandLandmarker)", has_landmarker, detail)
    except Exception as e:
        report("MediaPipe (Tasks API: HandLandmarker)", False, f"{type(e).__name__}: {e}")


def check_pyautogui():
    try:
        import pyautogui
        report("PyAutoGUI", True, f"version {package_version('pyautogui')}")
    except Exception as e:
        report("PyAutoGUI", False, f"{type(e).__name__}: {e}")


def check_tkinter():
    try:
        import tkinter
        report("Tkinter (for the window)", True, f"Tk {tkinter.TkVersion}")
    except Exception as e:
        report("Tkinter (for the window)", False, f"{type(e).__name__}: {e}")


def read_volume_percent():
    """Read the current Windows volume (0-100). Tries the new pycaw API, then the old one."""
    from pycaw.pycaw import AudioUtilities

    try:  # newer pycaw
        speakers = AudioUtilities.GetSpeakers()
        level = speakers.EndpointVolume.GetMasterVolumeLevelScalar()
        return round(level * 100), "new pycaw API"
    except Exception:
        pass

    from ctypes import POINTER, cast  # older pycaw
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    return round(volume.GetMasterVolumeLevelScalar() * 100), "old pycaw API"


def check_pycaw():
    if platform.system() != "Windows":
        skip("Pycaw (Windows volume)", "works on Windows only")
        return
    try:
        percent, style = read_volume_percent()
        report("Pycaw (Windows volume)", True,
               f"version {package_version('pycaw')}, current volume = {percent}% ({style})")
    except Exception as e:
        report("Pycaw (Windows volume)", False, f"{type(e).__name__}: {e}")


def check_camera():
    try:
        import cv2
        backend = getattr(cv2, "CAP_DSHOW", 0) if platform.system() == "Windows" else 0
        cap = cv2.VideoCapture(0, backend)
        if not cap.isOpened():
            report("Camera", False, "could not open camera 0 (is it used by another app?)")
            return
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            h, w = frame.shape[:2]
            report("Camera", True, f"read one frame, size {w}x{h}")
        else:
            report("Camera", False, "camera opened but returned no frame")
    except Exception as e:
        report("Camera", False, f"{type(e).__name__}: {e}")


def main():
    print("AirControl AI - environment check\n")
    check_python()
    check_opencv()
    check_numpy()
    check_mediapipe()
    check_pyautogui()
    check_tkinter()
    check_pycaw()
    if "--camera" in sys.argv:
        check_camera()
    else:
        skip("Camera", "run with --camera to test it")

    failed = results.count(False)
    print()
    if failed == 0:
        print("ALL CHECKS PASSED. The environment is ready.")
    else:
        print(f"{failed} check(s) FAILED. Copy this whole output and send it to your mentor.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
