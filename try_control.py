"""try_control.py
Live test of everything so far: camera -> hand -> gesture -> command -> Windows.
  Thumb up    = volume up (repeats while you hold it)
  Thumb down  = volume down
  Closed fist = pause the video
  Open palm   = play the video
Open a video and let it play BEFORE you start.

The Windows play/pause key is a TOGGLE and this program cannot see your video, so tell it the
starting state of the video:
  python try_control.py --on --video playing     (video is playing now)
  python try_control.py --on --video paused      (video is paused now)
  (without --video the state is UNKNOWN and the first fist / palm just presses the key)
Keys (click the video window first; use an ENGLISH keyboard layout):
  e or SPACE = turn control ON/OFF  (it starts OFF, so nothing changes until you press it)
  1 = "the video is PLAYING now"   2 = "the video is PAUSED now"   r = unknown
    (press them after you play/pause the video by hand with the mouse)
  q or ESC   = quit
No keys at all? Start it already ON with:   python try_control.py --on
(then close it by closing the PowerShell window or pressing Ctrl+C in PowerShell)
"""
import sys
import time

import cv2

from commands.command_mapper import CommandMapper
from commands.media_controller import MediaController
from commands.volume_controller import VolumeController
from models.types import Command, GestureType
from recognition.gesture_recognizer import GestureRecognizer
from recognition.gesture_stabilizer import GESTURE_HOLD, GestureStabilizer
from recognition.motion_filter import MotionFilter
from vision.camera_manager import CameraManager
from vision.hand_detector import HandDetector

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)


def percent(level):
    return "?" if level is None else f"{round(level * 100)}%"


def draw_overlay(frame, control_on, raw, stable, command, volume, is_playing, speed, steady, fps):
    """Write the control state, gesture, last command, volume and FPS on the frame."""
    cv2.putText(frame, "CONTROL: ON" if control_on else "CONTROL: OFF (press e / SPACE)",
                (10, 30), FONT, 0.8, GREEN if control_on else RED, 2)
    cv2.putText(frame, f"Gesture: {stable.name}", (10, 62), FONT, 0.8, GREEN, 2)
    cv2.putText(frame, f"Raw: {raw.name}", (10, 182), FONT, 0.6, WHITE, 2)
    change_text = "-" if speed is None else f"{speed:.2f}"
    cv2.putText(frame, f"Hand change: {change_text}  ({'STILL' if steady else 'MOVING - ignored'})",
                (10, 207), FONT, 0.6, GREEN if steady else RED, 2)
    cv2.putText(frame, f"Last command: {command.name}", (10, 92), FONT, 0.6, YELLOW, 2)
    cv2.putText(frame, f"Volume: {percent(volume)}", (10, 122), FONT, 0.8, YELLOW, 2)
    video = {True: "PLAYING", False: "PAUSED", None: "UNKNOWN"}[is_playing]
    cv2.putText(frame, f"Video (believed): {video}", (10, 152), FONT, 0.7, YELLOW, 2)
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
    motion = MotionFilter()
    mapper = CommandMapper()
    volume_controller = VolumeController()
    media = MediaController()
    if "--video" in sys.argv:
        value = sys.argv[sys.argv.index("--video") + 1:][:1]
        if value == ["playing"]:
            media.is_playing = True
        elif value == ["paused"]:
            media.is_playing = False
        else:
            print("WARNING: use  --video playing  or  --video paused  (ignored, state is UNKNOWN)")

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
        now = time.perf_counter()
        speed = motion.update(hand, now)
        # a hand that is moving (for example being raised) is not making a gesture
        raw = recognizer.recognize(hand) if motion.steady else GestureType.NONE
        stable = stabilizer.update(raw)
        command = mapper.map(stable)

        if command != Command.NONE:
            last_command = command
            if control_on:
                if command in (Command.VOLUME_UP, Command.VOLUME_DOWN):
                    if command == Command.VOLUME_UP:
                        volume = volume_controller.volume_up()
                    else:
                        volume = volume_controller.volume_down()
                    if volume is None:
                        print(f"WARNING: volume command failed: {volume_controller.last_error}")
                elif command in (Command.PLAY, Command.PAUSE):
                    media.execute(command)
                    if media.last_error:
                        print(f"WARNING: media key failed: {media.last_error}")

        fps = 1.0 / (now - previous_time) if now > previous_time else 0.0
        previous_time = now
        draw_overlay(frame, control_on, raw, stable, last_command, volume, media.is_playing, speed, motion.steady, fps)

        cv2.imshow("AirControl AI - control by gesture", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):
            break
        if key in (ord("e"), ord("E"), 32):
            control_on = not control_on
            print("Control is now", "ON" if control_on else "OFF")
        if key in (ord("r"), ord("R")):
            media.reset_state()
            print("Video state reset to UNKNOWN.")
        if key == ord("1"):
            media.is_playing = True
            print("Video state set to PLAYING.")
        if key == ord("2"):
            media.is_playing = False
            print("Video state set to PAUSED.")

    detector.close()
    camera.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
