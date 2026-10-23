"""VolumeController: reads and changes the Windows master volume (using Pycaw)."""
from ctypes import POINTER, cast

DEFAULT_STEP = 0.05  # one volume step = 5% of the full range


def open_default_endpoint():
    """Connect to the volume control of the default speakers (Windows only).

    Returns an object that has GetMasterVolumeLevelScalar() and SetMasterVolumeLevelScalar().
    Raises an error if Pycaw is missing or there is no audio device.
    """
    from pycaw.pycaw import AudioUtilities

    try:  # newer Pycaw: the speakers object already has the volume control
        return AudioUtilities.GetSpeakers().EndpointVolume
    except Exception:
        pass

    from comtypes import CLSCTX_ALL  # older Pycaw: we have to ask for it
    from pycaw.pycaw import IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


class VolumeController:
    """Volume is a number from 0.0 (silent) to 1.0 (full).

    No method here crashes the program: if the audio device is missing or Pycaw fails,
    the method returns None and the reason is saved in last_error (requirement NFR-07).
    """

    def __init__(self, step=DEFAULT_STEP, endpoint_factory=open_default_endpoint):
        self.step = step
        self.last_error = None
        self._endpoint_factory = endpoint_factory
        self._endpoint = None

    def _endpoint_or_connect(self):
        if self._endpoint is None:
            self._endpoint = self._endpoint_factory()
        return self._endpoint

    def get_volume(self):
        """Current volume (0.0 - 1.0), or None if it could not be read."""
        try:
            level = float(self._endpoint_or_connect().GetMasterVolumeLevelScalar())
            self.last_error = None
            return level
        except Exception as error:
            return self._fail(error)

    def set_volume(self, level):
        """Set the volume. The value is limited to 0.0 - 1.0. Returns the value that was set, or None."""
        level = max(0.0, min(1.0, float(level)))
        try:
            self._endpoint_or_connect().SetMasterVolumeLevelScalar(level, None)
            self.last_error = None
            return level
        except Exception as error:
            return self._fail(error)

    def change(self, delta):
        """Change the volume by delta (for example +0.05). Returns the new volume, or None."""
        current = self.get_volume()
        if current is None:
            return None
        return self.set_volume(current + delta)

    def volume_up(self):
        return self.change(+self.step)

    def volume_down(self):
        return self.change(-self.step)

    def _fail(self, error):
        self.last_error = f"{type(error).__name__}: {error}"
        self._endpoint = None  # connect again next time (the audio device may have changed)
        return None
