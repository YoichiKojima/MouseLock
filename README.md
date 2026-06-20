# Mouse Lock

A lightweight Windows utility that keeps your mouse cursor inside a chosen screen area. Useful for gaming, presentations, kiosk setups, or any time you want to stop the pointer from wandering onto another monitor or off-screen.

## Features

- **Area lock** — Constrain the cursor to a rectangular region using the Windows `ClipCursor` API
- **Drag-to-select** — Pick an area with a dimmed overlay; click without dragging to lock to the current monitor
- **Global hotkeys** — Select, toggle lock, and cancel selection without focusing the app
- **System tray** — Run quietly in the background with quick access from the notification area
- **Remembrance** — Unlock and re-lock to the same area without selecting again
- **Session-aware** — Re-applies the clip after you unlock your workstation
- **Customizable** — Change hotkeys, overlay opacity, and optional Windows startup in Settings
- **Single instance** — Only one copy runs at a time

## Requirements

- Windows 10 or later
- Python 3.12+ (for running from source)

## Download

Pre-built releases are available on the [Releases](https://github.com/YoichiKojima/MouseLock/releases) page. Download `MouseLock.exe` and run it — no install required.

## Usage

1. Start Mouse Lock (from source or the `.exe`).
2. Press **Alt+X** (default) to enter area selection mode.
3. Drag a rectangle on screen, or click once to lock to the current monitor.
4. Press **Alt+Z** (default) to toggle the lock on or off.
5. Press **Esc** during selection to cancel.

Right-click the tray icon for **Select area**, **Toggle lock**, **Settings**, and **Exit**.

## Default Hotkeys

| Action           | Default |
|------------------|---------|
| Select area      | Alt+X   |
| Toggle lock      | Alt+Z   |
| Cancel selection | Esc     |

Hotkeys can be changed in **Settings** (tray menu). Settings are saved to:

- **Installed / frozen app:** `%APPDATA%\MouseLock\settings.json`
- **Running from source:** `settings.json` in the project root

## Settings

- **Select hotkey** — Start area selection
- **Toggle hotkey** — Lock or unlock using the last selected area
- **Overlay opacity** — Dimming strength during area selection (0–100%)
- **Start with Windows** — Register in the Windows Run key so Mouse Lock starts at logon

## Run from Source

```bash
git clone https://github.com/YoichiKojima/MouseLock.git
cd MouseLock
pip install -r requirements.txt
python main.py
```

Run with administrator privileges if global hotkeys do not register reliably.

## Build

```bash
pip install -r requirements.txt
python -m PyInstaller MouseLock.spec
```

The executable is written to `dist/MouseLock.exe`.

## How It Works

Mouse Lock uses Win32 `ClipCursor` to restrict pointer movement. During selection, a layered overlay covers all monitors and a low-level mouse hook tracks drag gestures. Global hotkeys are handled via the `keyboard` library; the app stays in the system tray with `pystray`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
