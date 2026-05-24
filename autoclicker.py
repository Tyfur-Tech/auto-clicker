"""
Minimal auto clicker -- Tkinter + pynput.

A small, dependency-light alternative to OP Auto Clicker. Repeats a mouse
click at a configured interval until stopped or a target count is reached.
Start/stop is also toggleable via a global hotkey (default F6).
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput import keyboard
from pynput.mouse import Button, Controller as MouseController


# Global hotkey that toggles start/stop from anywhere.
HOTKEY_KEY = keyboard.Key.f6
HOTKEY_LABEL = "F6"

# Map of UI label -> pynput Button. Dict iteration order is insertion order
# (Python 3.7+), so this also drives the dropdown order.
BUTTONS = {
    "Left": Button.left,
    "Middle": Button.middle,
    "Right": Button.right,
}

# Map of UI label -> click count passed to mouse.click().
CLICK_TYPES = {"Single": 1, "Double": 2}

# Countdown shown in the status bar when picking a fixed location.
PICK_COUNTDOWN_SECONDS = 3

# How often the UI polls the worker thread to refresh status / detect exit.
POLL_INTERVAL_MS = 100

# Maximum slice the worker sleeps between stop-event checks. Keeps the worker
# responsive to Stop even when the configured interval is very large.
MAX_SLEEP_SLICE = 0.05


class AutoClicker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.geometry("360x420")
        self.root.resizable(False, False)

        self.mouse = MouseController()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.click_count = 0
        # Tracks whether the hotkey is currently held down so we ignore the
        # OS-level autorepeat keydown stream (otherwise holding F6 spams
        # toggles).
        self._hotkey_held = False

        self._build_ui()
        self._start_hotkey()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_status("Ready")

    # ---- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 6, "pady": 4}

        # --- Interval (H / M / S / MS) --------------------------------------
        interval = ttk.LabelFrame(self.root, text="Click interval")
        interval.pack(fill="x", **pad)

        self.hours_var = tk.StringVar(value="0")
        self.mins_var = tk.StringVar(value="0")
        self.secs_var = tk.StringVar(value="0")
        self.ms_var = tk.StringVar(value="100")

        for col, (label, var) in enumerate([
            ("Hours", self.hours_var),
            ("Mins", self.mins_var),
            ("Secs", self.secs_var),
            ("MS", self.ms_var),
        ]):
            ttk.Label(interval, text=label).grid(row=0, column=col, padx=4, pady=(4, 0))
            ttk.Entry(interval, textvariable=var, width=6).grid(row=1, column=col, padx=4, pady=(0, 4))

        # --- Click options (button + type) ----------------------------------
        opts = ttk.LabelFrame(self.root, text="Click options")
        opts.pack(fill="x", **pad)

        ttk.Label(opts, text="Button:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.button_var = tk.StringVar(value="Left")
        ttk.Combobox(
            opts, textvariable=self.button_var, values=list(BUTTONS),
            state="readonly", width=8,
        ).grid(row=0, column=1, padx=4)

        ttk.Label(opts, text="Type:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.type_var = tk.StringVar(value="Single")
        ttk.Combobox(
            opts, textvariable=self.type_var, values=list(CLICK_TYPES),
            state="readonly", width=8,
        ).grid(row=0, column=3, padx=4)

        # --- Repeat ----------------------------------------------------------
        repeat = ttk.LabelFrame(self.root, text="Repeat")
        repeat.pack(fill="x", **pad)

        self.repeat_mode = tk.StringVar(value="until")
        ttk.Radiobutton(
            repeat, text="Repeat", variable=self.repeat_mode, value="n",
        ).grid(row=0, column=0, padx=4, pady=2, sticky="w")
        self.repeat_n_var = tk.StringVar(value="100")
        ttk.Entry(repeat, textvariable=self.repeat_n_var, width=8).grid(row=0, column=1)
        ttk.Label(repeat, text="times").grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(
            repeat, text="Repeat until stopped", variable=self.repeat_mode, value="until",
        ).grid(row=1, column=0, columnspan=3, padx=4, pady=2, sticky="w")

        # --- Cursor position -------------------------------------------------
        cursor = ttk.LabelFrame(self.root, text="Cursor position")
        cursor.pack(fill="x", **pad)

        self.cursor_mode = tk.StringVar(value="current")
        ttk.Radiobutton(
            cursor, text="Current location", variable=self.cursor_mode, value="current",
        ).grid(row=0, column=0, columnspan=5, padx=4, pady=2, sticky="w")
        ttk.Radiobutton(
            cursor, text="Fixed", variable=self.cursor_mode, value="fixed",
        ).grid(row=1, column=0, padx=4, pady=2, sticky="w")

        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        ttk.Label(cursor, text="X:").grid(row=1, column=1, sticky="e")
        ttk.Entry(cursor, textvariable=self.x_var, width=6).grid(row=1, column=2)
        ttk.Label(cursor, text="Y:").grid(row=1, column=3, sticky="e", padx=(6, 0))
        ttk.Entry(cursor, textvariable=self.y_var, width=6).grid(row=1, column=4)
        ttk.Button(
            cursor, text="Pick location", command=self._pick_location,
        ).grid(row=2, column=0, columnspan=5, padx=4, pady=2, sticky="ew")

        # --- Controls --------------------------------------------------------
        controls = ttk.Frame(self.root)
        controls.pack(fill="x", **pad)
        self.start_btn = ttk.Button(controls, text="Start", command=self.start)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=4)
        self.stop_btn = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=4)

        ttk.Label(self.root, text=f"Hotkey: {HOTKEY_LABEL} (toggle start/stop)").pack(
            anchor="w", padx=10, pady=(0, 2),
        )

        # --- Status bar ------------------------------------------------------
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.root, textvariable=self.status_var, relief="sunken", anchor="w",
        ).pack(side="bottom", fill="x")

    # ---- Status helpers -----------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _running_status(self) -> None:
        self._set_status(f"Running... ({self.click_count} clicks)")

    # ---- Input validation ---------------------------------------------------

    def _read_interval_seconds(self) -> float:
        try:
            h = int(self.hours_var.get())
            m = int(self.mins_var.get())
            s = int(self.secs_var.get())
            ms = int(self.ms_var.get())
        except ValueError:
            raise ValueError("Interval fields must be integers")
        if min(h, m, s, ms) < 0:
            raise ValueError("Interval fields must be non-negative")
        total_ms = h * 3_600_000 + m * 60_000 + s * 1000 + ms
        if total_ms < 1:
            raise ValueError("Interval must be at least 1 ms")
        return total_ms / 1000.0

    def _read_repeat_n(self) -> int | None:
        if self.repeat_mode.get() != "n":
            return None
        try:
            n = int(self.repeat_n_var.get())
        except ValueError:
            raise ValueError("Repeat count must be an integer")
        if n <= 0:
            raise ValueError("Repeat count must be > 0")
        return n

    def _read_fixed_pos(self) -> tuple[int, int] | None:
        if self.cursor_mode.get() != "fixed":
            return None
        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
        except ValueError:
            raise ValueError("X and Y must be integers")
        return x, y

    # ---- Pick location ------------------------------------------------------

    def _pick_location(self) -> None:
        # Switch to fixed mode so the captured coords are actually used.
        self.cursor_mode.set("fixed")

        def tick(n: int) -> None:
            if n > 0:
                self._set_status(f"Move cursor... capturing in {n}")
                self.root.after(1000, tick, n - 1)
            else:
                x, y = self.mouse.position
                self.x_var.set(str(int(x)))
                self.y_var.set(str(int(y)))
                self._set_status(f"Captured ({int(x)}, {int(y)})")

        tick(PICK_COUNTDOWN_SECONDS)

    # ---- Start / stop -------------------------------------------------------

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            interval = self._read_interval_seconds()
            target_n = self._read_repeat_n()
            fixed_pos = self._read_fixed_pos()
        except ValueError as e:
            self._set_status(f"Error: {e}")
            return

        button = BUTTONS[self.button_var.get()]
        click_n = CLICK_TYPES[self.type_var.get()]
        self.click_count = 0
        self.stop_event.clear()
        self.worker = threading.Thread(
            target=self._run_clicks,
            args=(interval, target_n, fixed_pos, button, click_n),
            daemon=True,
        )
        self.worker.start()

        self.start_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])
        self._running_status()
        self._poll_worker()

    def stop(self) -> None:
        # Just signal -- the worker exits on its next stop-event check, and
        # the running _poll_worker tick re-enables the buttons.
        self.stop_event.set()

    def _poll_worker(self) -> None:
        if self.worker and self.worker.is_alive():
            self._running_status()
            self.root.after(POLL_INTERVAL_MS, self._poll_worker)
        else:
            self.start_btn.state(["!disabled"])
            self.stop_btn.state(["disabled"])
            self._set_status(f"Stopped ({self.click_count} clicks)")

    def _run_clicks(
        self,
        interval: float,
        target_n: int | None,
        fixed_pos: tuple[int, int] | None,
        button: Button,
        click_n: int,
    ) -> None:
        next_time = time.monotonic()
        while not self.stop_event.is_set():
            if fixed_pos is not None:
                self.mouse.position = fixed_pos
            self.mouse.click(button, click_n)
            self.click_count += 1

            if target_n is not None and self.click_count >= target_n:
                return

            # Sleep in slices so a Stop is honored quickly even when the
            # interval is long. wait() returns True if the event fires.
            next_time += interval
            while True:
                remaining = next_time - time.monotonic()
                if remaining <= 0:
                    break
                if self.stop_event.wait(min(remaining, MAX_SLEEP_SLICE)):
                    return

    # ---- Hotkey -------------------------------------------------------------

    def _start_hotkey(self) -> None:
        def on_press(key):
            # Ignore autorepeat keydowns -- only act on the first press
            # transition until the key is released.
            if key == HOTKEY_KEY and not self._hotkey_held:
                self._hotkey_held = True
                # Marshal back to the Tk main thread -- Tk widgets are not
                # thread-safe.
                self.root.after(0, self._toggle)

        def on_release(key):
            if key == HOTKEY_KEY:
                self._hotkey_held = False

        self.hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    def _toggle(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop()
        else:
            self.start()

    # ---- Shutdown -----------------------------------------------------------

    def _on_close(self) -> None:
        self.stop_event.set()
        try:
            self.hotkey_listener.stop()
        except Exception:
            pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AutoClicker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
