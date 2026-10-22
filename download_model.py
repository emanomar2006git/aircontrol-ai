"""download_model.py
Downloads the MediaPipe hand landmarker model into the assets folder
and checks that it loads. Run it once:  python download_model.py
"""
import sys
import urllib.request
from pathlib import Path

import mediapipe as mp

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).parent / "assets" / "hand_landmarker.task"
MIN_SIZE_BYTES = 1_000_000  # a real model is several MB; smaller means a broken download


def download():
    """Download the model file if it is not already there. Returns True on success."""
    MODEL_PATH.parent.mkdir(exist_ok=True)
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > MIN_SIZE_BYTES:
        print(f"Model already exists: {MODEL_PATH}")
        return True

    print("Downloading the hand model (a few MB)...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    except Exception as error:
        print(f"ERROR: download failed: {error}")
        MODEL_PATH.unlink(missing_ok=True)  # remove a half-downloaded file
        return False

    size = MODEL_PATH.stat().st_size
    if size < MIN_SIZE_BYTES:
        print(f"ERROR: the downloaded file is too small ({size} bytes).")
        MODEL_PATH.unlink(missing_ok=True)
        return False

    print(f"Saved to: {MODEL_PATH}  ({size / 1_000_000:.1f} MB)")
    return True


def check_model():
    """Try to load the model with MediaPipe. Returns True if it loads."""
    try:
        landmarker = mp.tasks.vision.HandLandmarker.create_from_model_path(str(MODEL_PATH))
        landmarker.close()
    except Exception as error:
        print(f"ERROR: the model file could not be loaded: {error}")
        return False
    print("OK: the model loads correctly. Ready for HandDetector.")
    return True


def main():
    if not download():
        print("\nManual option: open the MediaPipe 'Hand landmarker' page")
        print("(developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker),")
        print("download the model from the Models section, rename it to hand_landmarker.task")
        print("and put it inside the assets folder of the project.")
        sys.exit(1)
    if not check_model():
        sys.exit(1)


if __name__ == "__main__":
    main()
