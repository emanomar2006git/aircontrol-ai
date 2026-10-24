"""AppController: runs the whole per-frame process and keeps the state of the application.

It contains NO window code, so it can be tested without a screen and used by any user interface.
Per frame:  camera -> hand detector -> motion filter -> gesture recognizer -> stabilizer
            -> command mapper -> volume / media controller.
"""
import time
from dataclasses import dataclass

from models.types import Command, GestureType

VOLUME_REFRESH_SECONDS = 1.0   # how often we read the real volume (it can be changed by other apps)
CAMERA_MESSAGE = ("Camera not available. Close other apps that use the camera "
                  "(Zoom, Teams, browser), then click 'Retry camera'.")
DETECTOR_MESSAGE = "Hand detector could not start ({error}). Did you run:  python download_model.py"


@dataclass
class FrameResult:
    """Everything the user interface needs to show after one frame."""
    frame: object            # the camera image (BGR) with the hand skeleton drawn on it
    hand_found: bool
    raw: GestureType         # gesture of this single frame (only if the hand is still)
    stable: GestureType      # gesture after the stabilizer
    command: Command         # command of THIS frame (NONE most of the time)
    steady: bool             # True when the hand is still
    change: float            # how much the hand changed in the last 0.3 s (None if unknown)
    fps: float


class AppController:
    def __init__(self, camera=None, detector=None, detector_factory=None, recognizer=None,
                 stabilizer=None, motion=None, mapper=None, volume=None, media=None,
                 clock=time.perf_counter):
        # Real parts are created here unless the caller gives other ones (tests give fake parts).
        from commands.command_mapper import CommandMapper
        from commands.media_controller import MediaController
        from commands.volume_controller import VolumeController
        from recognition.gesture_recognizer import GestureRecognizer
        from recognition.gesture_stabilizer import GESTURE_HOLD, GestureStabilizer
        from recognition.motion_filter import MotionFilter
        from vision.camera_manager import CameraManager

        self.camera = camera or CameraManager()
        self.detector = detector
        self._detector_factory = detector_factory or self._default_detector_factory
        self.recognizer = recognizer or GestureRecognizer()
        self.stabilizer = stabilizer or GestureStabilizer(per_gesture=GESTURE_HOLD)
        self.motion = motion or MotionFilter()
        self.mapper = mapper or CommandMapper()
        self.volume = volume or VolumeController()
        self.media = media or MediaController()
        self._clock = clock

        self.enabled = False            # safe start: gestures are shown but do nothing until you enable
        self.running = False
        self.message = "Not started."
        self.last_command = Command.NONE
        self.volume_level = None        # 0.0 - 1.0, or None if unknown
        self.fps = 0.0
        self._last_time = None
        self._last_volume_check = None

    @staticmethod
    def _default_detector_factory():
        from vision.hand_detector import HandDetector  # imported here, so a missing MediaPipe gives a clear message
        return HandDetector()

    # ---------- start / stop ----------
    def start(self):
        """Open the camera and the hand detector. Returns True if everything is ready."""
        if self.running:
            return True
        if not self.camera.open():
            self.message = CAMERA_MESSAGE
            return False
        if self.detector is None:
            try:
                self.detector = self._detector_factory()
            except Exception as error:
                self.camera.release()
                self.message = DETECTOR_MESSAGE.format(error=error)
                return False
        self.stabilizer.reset()
        self.mapper.reset()
        self.motion.reset()
        self._last_time = None
        self._last_volume_check = None
        self._refresh_volume(force=True)
        self.running = True
        self.message = "Running."
        if self.volume_level is None:
            self.message += f" (Volume is not available: {self.volume.last_error})"
        return True

    def stop(self):
        """Close the camera and the detector. Safe to call more than once."""
        self.running = False
        if self.detector is not None:
            try:
                self.detector.close()
            except Exception:
                pass
            self.detector = None
        self.camera.release()

    # ---------- user settings ----------
    def set_enabled(self, enabled):
        """Turn the control of the PC on or off. Gestures are still recognized while it is off."""
        self.enabled = bool(enabled)
        self.message = "Control enabled." if self.enabled else "Control disabled."

    @property
    def video_state(self):
        """True = the video is believed to be playing, False = paused, None = unknown."""
        return self.media.is_playing

    def set_video_state(self, playing):
        """Tell the program what the video is doing now (the media key is only a toggle)."""
        self.media.is_playing = playing

    # ---------- the per-frame process ----------
    def process_frame(self):
        """Read one frame and run everything. Returns a FrameResult, or None if the camera is lost / not started."""
        if not self.running:
            return None
        frame = self.camera.read_frame()
        if frame is None:
            self.stop()
            self.message = "Camera lost. Click 'Retry camera'."
            return None

        try:
            hand = self.detector.detect(frame)
        except Exception as error:
            hand = None
            self.message = f"Detection error: {error}"
        else:
            self.detector.draw_landmarks(frame, hand)

        now = self._clock()
        change = self.motion.update(hand, now)
        raw = self.recognizer.recognize(hand) if self.motion.steady else GestureType.NONE
        stable = self.stabilizer.update(raw)
        command = self.mapper.map(stable)
        if command != Command.NONE:
            self.last_command = command
            if self.enabled:
                self._execute(command)

        self._update_fps(now)
        self._refresh_volume()
        return FrameResult(frame=frame, hand_found=hand is not None, raw=raw, stable=stable,
                           command=command, steady=self.motion.steady, change=change, fps=self.fps)

    # ---------- helpers ----------
    def _execute(self, command):
        if command in (Command.VOLUME_UP, Command.VOLUME_DOWN):
            level = self.volume.volume_up() if command == Command.VOLUME_UP else self.volume.volume_down()
            if level is None:
                self.message = f"Volume error: {self.volume.last_error}"
            else:
                self.volume_level = level
                self.message = f"{command.name}: volume is now {round(level * 100)}%."
        elif command in (Command.PLAY, Command.PAUSE):
            sent = self.media.execute(command)
            if self.media.last_error:
                self.message = f"Media key error: {self.media.last_error}"
            elif sent:
                self.message = f"{command.name}: media key sent."
            else:
                self.message = f"{command.name}: ignored (the video is already {'playing' if command == Command.PLAY else 'paused'}, or too soon after the last key)."

    def _update_fps(self, now):
        if self._last_time is not None and now > self._last_time:
            current = 1.0 / (now - self._last_time)
            self.fps = current if self.fps == 0 else 0.9 * self.fps + 0.1 * current
        self._last_time = now

    def _refresh_volume(self, force=False):
        now = self._clock()
        if force or self._last_volume_check is None or now - self._last_volume_check >= VOLUME_REFRESH_SECONDS:
            self._last_volume_check = now
            level = self.volume.get_volume()
            if level is not None:
                self.volume_level = level
