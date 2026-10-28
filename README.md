# AirControl AI

Control your Windows PC with hand gestures. The laptop camera sees your hand, and the app changes the
system volume or plays/pauses a video - no keyboard or mouse needed.

Built with Python, OpenCV, MediaPipe (Hand Landmarker), Pycaw, PyAutoGUI and Tkinter.

## Features

| Gesture | Action |
|---|---|
| Thumb up (hold) | Volume up (repeats while held) |
| Thumb down (hold) | Volume down (repeats while held) |
| Open palm (hold) | Play video |
| Closed fist (hold) | Pause video |

- Moving hands are ignored on purpose: the hand must be held still, so waving does not trigger anything.
- The app can be turned on/off with the **Space** key. **Esc** closes it.
- The window shows the camera image, the hand skeleton, the detected gesture, the last command and the FPS.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- A webcam

## Installation

```powershell
git clone https://github.com/emanomar2006git/aircontrol-ai.git
cd aircontrol-ai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python download_model.py
```

`download_model.py` downloads the MediaPipe hand model file once (internet needed).

## Run

```powershell
venv\Scripts\activate
python main.py
```

Tips: use good front lighting, keep only one person in the camera view, and hold the gesture still
for about half a second.

## Tests

```powershell
python -m unittest discover -s tests -t .
```

131 automated tests (they use fake camera / audio, so no hardware is needed).

## Tools

| File | Purpose |
|---|---|
| `accuracy_test.py` | Measures gesture accuracy (`--trials N`) and false triggers (`--idle`) |
| `measure_speed.py` | Measures the FPS of the camera + detection pipeline |
| `measure_ui_speed.py` | Measures the FPS of the full window |
| `try_camera_modes.py` | Compares camera modes |
| `calibrate_gestures.py` | Shows the raw numbers behind each gesture |

## Project structure

```
main.py            entry point
core/              AppController (the brain, no UI code)
vision/            CameraManager, HandDetector
recognition/       MotionFilter, GestureRecognizer, GestureStabilizer
commands/          CommandMapper, VolumeController, MediaController
ui/                MainWindow (Tkinter)
models/            shared types
tests/             unit tests
docs/              SRS, Use Cases, Design, Test Plan
```

## Known limitations

- The app does not read the real player state; it assumes play/pause state from its own commands.
- Tested by one user (24 attempts, 100% on the final run); weak light or two people in view lower accuracy.
- Features FR-13 and FR-14 (see SRS) are not implemented.
- There is no Stop button for the camera; use Esc or close the window.

## Documents

See the `docs/` folder: SRS, Use Cases, Design (v1.1), Test Plan.

## Author

[Student Name]
