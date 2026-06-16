import keyboard

from mouselock.settings_store import load


def validate_hotkey(hotkey):
    hotkey = hotkey.strip().lower()
    if not hotkey:
        return False, "Hotkey cannot be empty."
    try:
        keyboard.parse_hotkey(hotkey)
    except (ValueError, KeyError):
        return False, f'"{hotkey}" is not a valid key combination.'
    return True, ""


def apply_hotkeys(select_cb, toggle_cb, cancel_cb):
    settings = load()
    keyboard.unhook_all()
    keyboard.add_hotkey(settings["select_hotkey"], select_cb)
    keyboard.add_hotkey(settings["toggle_hotkey"], toggle_cb)
    keyboard.add_hotkey("esc", cancel_cb)
    return settings
