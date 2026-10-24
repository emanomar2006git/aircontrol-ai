"""try_volume_gesture.py
Live test: camera -> hand -> gesture -> command -> Windows volume.
  Thumb up   = volume up (repeats while you hold it)
  Thumb down = volume down
  (Closed fist / open palm are shown as PAUSE / PLAY but do nothing yet: that is Phase 8.)
Keys (click the video window first; use an ENGLISH keyboard layout):
  e or SPACE = turn control ON/OFF  (it starts OFF, so nothing changes until you press it)
  q or ESC   = quit
No keys at all? Start it already ON with:   python try_volume_gesture.py --on
(then close it by closing the PowerShell window or pressing Ctrl+C in PowerShell)
"""
import sys
import time

import cv2

from commands.command_mapper import CommandMapper
from commands.volume_controller import VolumeController
from models.types import Command
from recognition.gesture_recognizer import GestureRecognizer
from recognition.gesture_stabilizer import GESTURE_HOLD, GestureStabilizer
from vision.camera_manager import CameraManager
from vision.hand_detector import HandDetector

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)


def percent(level):
    return "?" if level is None else f"{round(level * 100)}%"


def draw_overlay(frame, control_on, stable, command, volume, fps):
    """Write the control state, gesture, last command, volume and FPS on the frame."""
    cv2.putText(frame, "CONTROL: ON" if control_on else "CONTROL: OFF (press e / SPACE)",
                (10, 30), FONT, 0.8, GREEN if control_on else RED, 2)
    cv2.putText(frame, f"Gesture: {stable.name}", (10, 62), FONT, 0.8, GREEN, 2)
    cv2.putText(frame, f"Last command: {command.name}", (10, 92), FONT, 0.6, YELLOW, 2)
    cv2.putText(frame, f"Volume: {percent(volume)}", (10, 122), FONT, 0.8, YELLOW, 2)
    cv2.putText(frame, f"FPS: {fps:.0f}", (10, frame.shape[0] - 15), FONT, 0.7, WHITE, 2)


def main():
    camera = CameraManager()
    if not camera.open():
        print("ERROR: could not open the camera. Close other apps that use it and try again.")
        return

    try:
        detector = HandDetector()
    except Exception as error:
        print(f"ERROR: could not start the hand detector: {error}")
        print("Did you run  python download_model.py  first?")
        camera.release()
        return

    recognizer = GestureRecognizer()
    stabilizer = GestureStabilizer(per_gesture=GESTURE_HOLD)
    mapper = CommandMapper()
    volume_controller = VolumeController()

    control_on = "--on" in sys.argv
    last_command = Command.NONE
    volume = volume_controller.get_volume()
    if volume is None:
        print(f"WARNING: cannot read the volume ({volume_controller.last_error}).")
    print("Started. Control is", "ON." if control_on else "OFF. Click the video window and press 'e' (or SPACE) to turn it ON.")
    print("Quit with 'q' or ESC (video window must be selected), or Ctrl+C in this window.")
    previous_time = time.perf_counter()

    while True:
        frame = camera.read_frame()
        if frame is None:
            print("ERROR: lost the camera.")
            break

        hand = detector.detect(frame)
        detector.draw_landmarks(frame, hand)
        stable = stabilizer.update(recognizer.recognize(hand))
        command = mapper.map(stable)

        if command != Command.NONE:
            last_command = command
            if control_on:
                if command == Command.VOLUME_UP:
                    volume = volume_controller.volume_up()
                elif command == Command.VOLUME_DOWN:
                    volume = volume_controller.volume_down()
                if volume is None:
                    print(f"WARNING: volume command failed: {volume_controller.last_error}")

        now = time.perf_counter()
        fps = 1.0 / (now - previous_time) if now > previous_time else 0.0
        previous_time = now
        draw_overlay(frame, control_on, stable, last_command, volume, fps)

        cv2.imshow("AirControl AI - volume by gesture", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):
            break
        if key in (ord("e"), ord("E"), 32):
            control_on = not control_on
            print("Control is now", "ON" if control_on else "OFF")

    detector.close()
    camera.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
