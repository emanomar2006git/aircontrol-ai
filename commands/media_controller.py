"""MediaController: play / pause the video with the Windows Play/Pause media key (PyAutoGUI)."""
import time

from models.types import Command

DEFAULT_MIN_INTERVAL = 1.0  # seconds: no two key presses closer than this (FR-12 cooldown)


def send_play_pause_key():
    """Press the Windows Play/Pause media key (the same key as on a multimedia keyboard)."""
    import pyautogui

    pyautogui.press("playpause")


class MediaController:
    """Plays or pauses the video that Windows currently treats as the active media.

    IMPORTANT: the Windows key is a TOGGLE. One press pauses a playing video, and the same press
    plays a paused one. The key cannot say "play" or "pause" by itself.
    So this class remembers what it believes the state is (is_playing):
      - True  : playing,   False : paused,   None : unknown (nothing was sent yet).
    play() sends the key only if the video is not already playing, and pause() only if it
    is not already paused. When the state is unknown, the first command is always sent.
    If the video was changed by hand (mouse / keyboard), call reset_state().

    No method crashes the program: if the key cannot be sent, it returns False and the
    reason is saved in last_error.
    """

    def __init__(self, key_press=send_play_pause_key, clock=None, min_interval=DEFAULT_MIN_INTERVAL):
        self._key_press = key_press
        self._clock = clock or time.monotonic
        self.min_interval = min_interval
        self.last_error = None
        self._last_press_time = None
        self.is_playing = None

    def reset_state(self):
        """Forget the remembered state (use it after you play/pause the video by hand)."""
        self.is_playing = None

    def play(self):
        """Returns True if a key press was sent."""
        if self.is_playing is True:
            return False
        return self._press(new_state=True)

    def pause(self):
        """Returns True if a key press was sent."""
        if self.is_playing is False:
            return False
        return self._press(new_state=False)

    def execute(self, command):
        """Run a Command. Returns True if a key press was sent. Other commands are ignored."""
        if command == Command.PLAY:
            return self.play()
        if command == Command.PAUSE:
            return self.pause()
        return False

    def _press(self, new_state):
        now = self._clock()
        if self._last_press_time is not None and now - self._last_press_time < self.min_interval:
            return False  # cooldown: too soon after the last key press
        try:
            self._key_press()
        except Exception as error:
            self.last_error = f"{type(error).__name__}: {error}"
            return False
        self.last_error = None
        self._last_press_time = now
        self.is_playing = new_state
        return True
