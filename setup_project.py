"""setup_project.py
Creates the AirControl AI folder structure inside the CURRENT folder.
Safe to run more than once: it never overwrites a file that already exists.
"""
from pathlib import Path

# Packages = folders that contain Python code (each gets an empty __init__.py)
PACKAGES = ["models", "vision", "recognition", "commands", "core", "ui", "tests"]
# Plain folders (no Python code)
PLAIN_FOLDERS = ["docs", "assets"]


def stub(description: str) -> str:
    """Return a small starting comment for a module that is still empty."""
    return f'"""{description}\n\nTODO: implemented in a later phase.\n"""\n'


FILES = {
    "main.py": stub("Entry point: starts the AirControl AI application."),
    "models/types.py": stub("Shared data types: HandData, GestureType, Command."),
    "vision/camera_manager.py": stub("CameraManager: opens, reads and releases the camera (OpenCV)."),
    "vision/hand_detector.py": stub("HandDetector: finds the hand and its 21 landmarks (MediaPipe)."),
    "recognition/gesture_recognizer.py": stub("GestureRecognizer: rule-based gesture recognition."),
    "recognition/gesture_stabilizer.py": stub("GestureStabilizer: hold time and cooldown."),
    "commands/command_mapper.py": stub("CommandMapper: maps a gesture to a command."),
    "commands/volume_controller.py": stub("VolumeController: controls Windows volume (Pycaw)."),
    "commands/media_controller.py": stub("MediaController: play/pause with media keys (PyAutoGUI)."),
    "core/app_controller.py": stub("AppController: keeps the state and runs the per-frame process."),
    "ui/main_window.py": stub("MainWindow: Tkinter user interface."),
    "docs/.gitkeep": "",
    "assets/.gitkeep": "",
    "requirements.txt": (
        "# AirControl AI - required libraries\n"
        "mediapipe>=0.10.30\n"
        "opencv-contrib-python>=4.8\n"
        "numpy\n"
        "pyautogui>=0.9.54\n"
        'pycaw; sys_platform == "win32"\n'
    ),
    ".gitignore": (
        "# virtual environment and caches\n"
        "venv/\n"
        "__pycache__/\n"
        "*.pyc\n"
        "# editor settings\n"
        ".vscode/\n"
        ".idea/\n"
        "# large model file (downloaded by the app, not stored in Git)\n"
        "assets/*.task\n"
    ),
    "README.md": (
        "# AirControl AI\n\n"
        "Control your computer with hand gestures using the laptop camera.\n\n"
        "## Setup (Windows)\n"
        "1. `python -m venv venv`\n"
        "2. `venv\\Scripts\\activate`\n"
        "3. `pip install -r requirements.txt`\n"
        "4. `python check_setup.py`\n\n"
        "## Status\n"
        "In development (Software Engineering course project).\n"
    ),
}


def main() -> None:
    root = Path.cwd()
    print(f"Creating project structure in: {root}\n")

    for name in PACKAGES:
        (root / name).mkdir(exist_ok=True)
        FILES[f"{name}/__init__.py"] = ""
    for name in PLAIN_FOLDERS:
        (root / name).mkdir(exist_ok=True)

    created, skipped = 0, 0
    for rel_path, content in sorted(FILES.items()):
        path = root / rel_path
        if path.exists():
            print(f"  skipped (already exists): {rel_path}")
            skipped += 1
        else:
            path.write_text(content, encoding="utf-8")
            print(f"  created: {rel_path}")
            created += 1

    print(f"\nDone. {created} file(s) created, {skipped} skipped.")


if __name__ == "__main__":
    main()
