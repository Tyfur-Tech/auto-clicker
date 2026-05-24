# Auto Clicker

A minimalistic desktop auto clicker. Repeats a mouse click at a user-defined
interval until you stop it (or until it reaches a target count). Written in
~330 lines of Python with Tkinter and `pynput` -- no other dependencies, no
telemetry, no internet access.

## Download (no Python required)

Grab the latest prebuilt binary for your OS from the
[Releases page](../../releases/latest):

| Platform | File | How to run |
| --- | --- | --- |
| Windows | `AutoClicker-Windows.exe` | Double-click it. The first time, Windows SmartScreen may say "unrecognized app" -- click **More info -> Run anyway**. |
| macOS | `AutoClicker-macOS.zip` | Unzip, drag `AutoClicker.app` into `Applications`, then open it. The first time, right-click -> **Open** to bypass Gatekeeper. Grant **Accessibility** + **Input Monitoring** in *System Settings -> Privacy & Security* (see notes below). |
| Linux | `AutoClicker-Linux` | `chmod +x AutoClicker-Linux && ./AutoClicker-Linux`. Requires an X11 session (Wayland may not capture global hotkeys). |

That's it -- no Python, no `pip`, no terminal needed for the end user.

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

## Run from source

Requires Python 3.10+.

```
pip install -r requirements.txt
python autoclicker.py
```

Press the **Start** button (or `F6`) to begin clicking, and **Stop**
(or `F6` again) to halt.

## Build a binary yourself

You only need this if you don't want to use the prebuilt downloads.

```
pip install -r requirements-dev.txt
pyinstaller --onefile --windowed --name AutoClicker autoclicker.py
```

The result lands in `dist/`:

- Windows -> `dist/AutoClicker.exe`
- macOS -> `dist/AutoClicker.app`
- Linux -> `dist/AutoClicker`

## Releasing (maintainers)

A GitHub Actions workflow (`.github/workflows/build.yml`) builds all three
platforms automatically. To cut a release:

```
git tag v0.1.0
git push origin v0.1.0
```

The workflow runs on every tag matching `v*`, builds on Windows, macOS, and
Linux runners, and uploads the binaries to the matching GitHub Release. You
can also trigger it manually from the Actions tab via *Run workflow*; in that
case the artifacts are attached to the workflow run instead of a release.

## Platform notes

- **Windows / Linux**: works out of the box.
- **macOS**: grant the app (or the Python interpreter, if running from
  source) both **Accessibility** and **Input Monitoring** permissions in
  *System Settings -> Privacy & Security*. Without these, `pynput` cannot
  send clicks or receive the global hotkey.
- **Antivirus**: PyInstaller `--onefile` binaries are occasionally
  misflagged by Windows antivirus heuristics. The source is right here -- if
  you're unsure, build it yourself.

## License

[MIT](LICENSE) -- do whatever you want with it.
