# Auto Clicker

A minimalistic desktop auto clicker. Repeats a mouse click at a user-defined
interval until you stop it (or until it reaches a target count). Written in
~300 lines of Python with Tkinter and `pynput` -- no other dependencies, no
telemetry, no internet access.

## Features

- Interval set in hours / minutes / seconds / milliseconds (default 100 ms).
- Left, middle, or right click; single or double.
- Repeat N times, or repeat until stopped.
- Click at the current cursor location, or at a fixed (X, Y) point. The
  "Pick location" button counts down for a few seconds and then captures
  the cursor's current position into the X/Y fields.
- Global hotkey (default `F6`) toggles start/stop from anywhere -- the
  app does not need to be focused.
- Compact ~360x420 window, single file.

## Install

Requires Python 3.10+.

```
pip install -r requirements.txt
```

## Run

```
python autoclicker.py
```

Press the **Start** button (or `F6`) to begin clicking, and **Stop**
(or `F6` again) to halt.

## Platform notes

- **Windows / Linux**: works out of the box.
- **macOS**: grant the Python interpreter (or your terminal app) both
  **Accessibility** and **Input Monitoring** permissions in
  *System Settings -> Privacy & Security*. Without these, `pynput` cannot
  send clicks or receive the global hotkey.
