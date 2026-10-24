"""MainWindow: the Tkinter window of AirControl AI."""
import tkinter as tk
from tkinter import ttk

import cv2

from models.types import Command, GestureType

GREEN = "#1b8f3a"
RED = "#c62828"
GREY = "#555555"
VIDEO_WIDTH, VIDEO_HEIGHT = 640, 480
PANEL_WIDTH = 300
LOOP_DELAY_MS = 1   # wait before the next frame (the work itself takes about 30 ms)
SHOW_EVERY = 2      # draw the picture every 2nd frame: drawing costs about 25 ms, and the FPS matters (NFR-01)


class MainWindow:
    """Shows the camera and the state, and lets the user enable/disable the control.

    The window only SHOWS things and passes the user's clicks to the AppController.
    All the real work is done in AppController.process_frame(), once per tick.
    """

    def __init__(self, controller, root=None):
        self.controller = controller
        self.root = root or tk.Tk()
        self.root.title("AirControl AI")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._photo = None       # we must keep a reference, or Tk throws the image away
        self._after_id = None
        self._closed = False
        self._frame_number = 0
        self._build()

    # ---------- building the window ----------
    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=0)
        left = tk.Frame(root)
        left.grid(row=0, column=0, padx=8, pady=8)
        # A fixed-size frame holds the picture. (A Label's width/height are in letters while it shows
        # text but in pixels while it shows an image, so we size the frame instead of the label.)
        video_frame = tk.Frame(left, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, bg="#222222")
        video_frame.pack_propagate(False)
        video_frame.pack()
        self.video_label = tk.Label(video_frame, text="Camera is off", bg="#222222", fg="white")
        self.video_label.pack(fill="both", expand=True)

        panel = tk.Frame(root, width=PANEL_WIDTH)
        panel.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="n")

        self.control_label = tk.Label(panel, text="CONTROL: DISABLED", font=("Segoe UI", 15, "bold"), fg=RED)
        self.control_label.pack(anchor="w", pady=(0, 4))
        self.toggle_button = ttk.Button(panel, text="Enable control (Space)", command=self.toggle_enabled)
        self.toggle_button.pack(fill="x", pady=(0, 12))

        self.gesture_label = self._info(panel, "Gesture: -")
        self.command_label = self._info(panel, "Last command: -")
        self.hand_label = self._info(panel, "Hand: not found")

        self.volume_label = self._info(panel, "Volume: ?")
        self.volume_bar = ttk.Progressbar(panel, maximum=100, length=PANEL_WIDTH)
        self.volume_bar.pack(fill="x", pady=(0, 12))

        self.video_state_label = self._info(panel, "Video (believed): UNKNOWN")
        buttons = tk.Frame(panel)
        buttons.pack(fill="x", pady=(0, 12))
        for text, value in (("Playing", True), ("Paused", False), ("Unknown", None)):
            ttk.Button(buttons, text=text, width=9, command=lambda v=value: self.set_video_state(v)).pack(side="left", padx=(0, 4))

        self.fps_label = self._info(panel, "FPS: -")
        self.retry_button = ttk.Button(panel, text="Retry camera", command=self.retry_camera)
        self.retry_button.pack(fill="x", pady=(12, 4))
        ttk.Button(panel, text="Quit (Esc)", command=self.close).pack(fill="x")

        self.status_label = tk.Label(root, text="", anchor="w", justify="left", wraplength=VIDEO_WIDTH + PANEL_WIDTH,
                                     fg=GREY, relief="sunken")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="we", padx=8, pady=(0, 8))

        root.bind("<space>", lambda event: self.toggle_enabled())
        root.bind("<Escape>", lambda event: self.close())

    @staticmethod
    def _info(parent, text):
        label = tk.Label(parent, text=text, anchor="w", font=("Segoe UI", 11))
        label.pack(fill="x", pady=1)
        return label

    # ---------- user actions ----------
    def toggle_enabled(self):
        self.controller.set_enabled(not self.controller.enabled)
        self._refresh_texts()

    def set_video_state(self, playing):
        self.controller.set_video_state(playing)
        self._refresh_texts()

    def retry_camera(self):
        if self.controller.start():
            self._schedule()
        self._refresh_texts()

    # ---------- the loop ----------
    def run(self):
        """Start the camera and show the window until it is closed."""
        self.controller.start()
        self._refresh_texts()
        self._schedule()
        self.root.mainloop()

    def _schedule(self):
        if self._after_id is None and not self._closed:
            self._after_id = self.root.after(LOOP_DELAY_MS, self._tick)

    def _tick(self):
        """One step of the loop: process one frame and show the result."""
        self._after_id = None
        if self._closed:
            return
        result = self.controller.process_frame()
        if result is not None:
            self._frame_number += 1
            if self._frame_number % SHOW_EVERY == 1 or SHOW_EVERY == 1:
                self._show_frame(result.frame)
            self._refresh_texts(result)
            self._schedule()
        else:
            self.video_label.configure(image="", text="Camera is off")
            self._photo = None
            self._refresh_texts()

    def _show_frame(self, frame):
        ok, buffer = cv2.imencode(".ppm", frame)   # PPM is fast to encode and Tk can read it directly
        if ok:
            self._photo = tk.PhotoImage(data=buffer.tobytes())
            self.video_label.configure(image=self._photo, text="")

    # ---------- showing the state ----------
    def _refresh_texts(self, result=None):
        c = self.controller
        self.control_label.configure(text="CONTROL: ENABLED" if c.enabled else "CONTROL: DISABLED",
                                     fg=GREEN if c.enabled else RED)
        self.toggle_button.configure(text="Disable control (Space)" if c.enabled else "Enable control (Space)")
        self.command_label.configure(text=f"Last command: {c.last_command.name if c.last_command != Command.NONE else '-'}")

        if result is not None:
            self.gesture_label.configure(text=f"Gesture: {result.stable.name if result.stable != GestureType.NONE else '-'}")
            if not result.hand_found:
                hand_text = "Hand: not found"
            else:
                hand_text = "Hand: still" if result.steady else "Hand: moving (ignored)"
            self.hand_label.configure(text=hand_text)
            self.fps_label.configure(text=f"FPS: {result.fps:.0f}")
        elif not c.running:
            self.gesture_label.configure(text="Gesture: -")
            self.hand_label.configure(text="Hand: not found")
            self.fps_label.configure(text="FPS: -")

        if c.volume_level is None:
            self.volume_label.configure(text="Volume: ?")
            self.volume_bar.configure(value=0)
        else:
            self.volume_label.configure(text=f"Volume: {round(c.volume_level * 100)}%")
            self.volume_bar.configure(value=c.volume_level * 100)

        video = {True: "PLAYING", False: "PAUSED", None: "UNKNOWN"}[c.video_state]
        self.video_state_label.configure(text=f"Video (believed): {video}")
        self.retry_button.state(["disabled"] if c.running else ["!disabled"])
        self.status_label.configure(text=c.message)

    # ---------- closing ----------
    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self.controller.stop()
        self.root.destroy()
