import os
import sys

if __name__ == "__main__":
    from mouselock.single_instance import acquire_instance

    if not acquire_instance():
        print("Mouse Lock is already running.")
        sys.exit(0)

import keyboard

from mouselock.hotkey_manager import apply_hotkeys, ensure_hotkeys
from mouselock.mouse_clip import apply_clip, unlock_mouse
from mouselock.mouse_hook import stop_mouse_pump, uninstall_mouse_hook
from mouselock.selection import close_overlay, end_selection_session, start_area_selection
from mouselock.settings_dialog import show_settings_dialog
from mouselock.settings_store import format_hotkey_label, load
from mouselock.windows_startup import ensure_registered
from mouselock.state import hook_active, hook_dragging, mouse_clip, root, session_state
from mouselock.tray import refresh_menu, remove_tray, setup_tray
from mouselock.win32 import user32


def is_workstation_locked():
    desktop = user32.OpenInputDesktop(0, False, 0)
    if desktop:
        user32.CloseDesktop(desktop)
        return False
    return True


def on_session_unlock():
    keyboard.stash_state()
    if mouse_clip["rect"] is not None:
        apply_clip()


def poll_session_state():
    locked = is_workstation_locked()
    if session_state["locked"] and not locked:
        on_session_unlock()
    session_state["locked"] = locked
    root.after(500, poll_session_state)


def poll_hotkeys():
    ensure_hotkeys()
    root.after(1000, poll_hotkeys)


def start_area_selection_async():
    root.after(0, start_area_selection)


def toggle_lock():
    from mouselock.mouse_clip import lock_mouse_to_area
    from mouselock.state import saved_lock_rect, selection

    if selection["active"]:
        return
    toggle_hotkey = format_hotkey_label(load()["toggle_hotkey"])
    if mouse_clip["rect"] is not None:
        unlock_mouse()
        print(f"Mouse unlocked. Press {toggle_hotkey} again to lock to the original area.")
    elif saved_lock_rect["rect"] is not None:
        x, y, width, height = saved_lock_rect["rect"]
        lock_mouse_to_area(x, y, width, height)
    else:
        select_hotkey = format_hotkey_label(load()["select_hotkey"])
        print(f"No lock area. Press {select_hotkey} to select an area first.")


def toggle_lock_async():
    root.after(0, toggle_lock)


def cancel_selection():
    from mouselock.state import selection

    if selection["active"]:
        end_selection_session(restore_original=True)


def cancel_selection_async():
    root.after(0, cancel_selection)


def register_hotkeys():
    apply_hotkeys(
        start_area_selection_async,
        toggle_lock_async,
        cancel_selection_async,
    )


def open_settings():
    def on_saved():
        register_hotkeys()
        refresh_menu()

    show_settings_dialog(on_saved)


def shutdown():
    keyboard.unhook_all()
    hook_active.value = 0
    hook_dragging.value = 0
    stop_mouse_pump()
    close_overlay(restore_focus=False)
    uninstall_mouse_hook()
    unlock_mouse()
    remove_tray()
    os._exit(0)


def main():
    settings = load()
    if settings["start_with_windows"]:
        try:
            ensure_registered()
        except OSError:
            pass

    register_hotkeys()

    if not setup_tray(
        start_area_selection_async,
        toggle_lock_async,
        open_settings,
        shutdown,
    ):
        print("System tray icon unavailable. Hotkeys still work.")

    session_state["locked"] = is_workstation_locked()
    root.after(500, poll_session_state)
    root.after(1000, poll_hotkeys)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
