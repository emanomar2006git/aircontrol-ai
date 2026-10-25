"""CameraManager: opens, reads and releases the camera (OpenCV)."""
import platform

import cv2


class CameraManager:
    """Wraps the camera so the rest of the app never touches OpenCV capture directly."""

    def __init__(self, camera_index=0, mirror=True, width=640, height=480, fourcc="YUY2", fps=30):
        self.camera_index = camera_index
        self.mirror = mirror
        # Settings found with try_camera_modes.py: asking for them explicitly gave 16 FPS instead of 10.
        # A camera that does not support one of them simply ignores it.
        self.width = width
        self.height = height
        self.fourcc = fourcc
        self.fps = fps
        self._capture = None

    def open(self):
        """Open the camera. Returns True on success, False on failure (never crashes)."""
        backend = getattr(cv2, "CAP_DSHOW", 0) if platform.system() == "Windows" else 0
        capture = cv2.VideoCapture(self.camera_index, backend)
        if not capture.isOpened():
            capture.release()
            return False
        self._apply_settings(capture)
        self._capture = capture
        return True

    def _apply_settings(self, capture):
        """Ask the camera for a fast, small picture mode (the camera may ignore what it cannot do)."""
        if self.fourcc:
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
        if self.width and self.height:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if self.fps:
            capture.set(cv2.CAP_PROP_FPS, self.fps)

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
