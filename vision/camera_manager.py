"""CameraManager: opens, reads and releases the camera (OpenCV)."""
import platform

import cv2


class CameraManager:
    """Wraps the camera so the rest of the app never touches OpenCV capture directly."""

    def __init__(self, camera_index=0, mirror=True):
        self.camera_index = camera_index
        self.mirror = mirror
        self._capture = None

    def open(self):
        """Open the camera. Returns True on success, False on failure (never crashes)."""
        backend = getattr(cv2, "CAP_DSHOW", 0) if platform.system() == "Windows" else 0
        capture = cv2.VideoCapture(self.camera_index, backend)
        if not capture.isOpened():
            capture.release()
            return False
        self._capture = capture
        return True

    def is_open(self):
        """True while the camera is open and ready."""
        return self._capture is not None and self._capture.isOpened()

    def read_frame(self):
        """Return one frame (mirrored if enabled), or None if no frame is available."""
        if not self.is_open():
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None
        if self.mirror:
            frame = cv2.flip(frame, 1)
        return frame

    def release(self):
        """Close the camera and free it for other apps."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None