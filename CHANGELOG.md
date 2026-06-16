# Change Logs

## v0.0.1

### Windows startup.

- Optional "Start with Windows" setting in Settings; saving adds or removes a Windows Run registry entry.
- Re-applies the Run entry on launch when enabled, keeping the path correct after updates or reinstalls.

### Settings.

- Settings dialog renamed from "Hotkey Settings" to "Settings".

## v0.0.0

### Initial release.

- Locks the mouse cursor to a rectangular screen area using the Windows `ClipCursor` API.
- Drag-to-select area picker with a dimmed overlay; a click without dragging locks to the current monitor.
- Global hotkeys to select an area, toggle lock on/off, and cancel selection with Esc (defaults: Alt+X, Alt+Z).
- System tray menu for select area, toggle lock, hotkey settings, and exit.
- Customizable select and toggle hotkeys, saved to `settings.json`.
- Remembers the last lock area so you can unlock and re-lock without reselecting.
- Re-applies the clip after the workstation is unlocked.
- Single-instance guard prevents multiple copies from running at once.

