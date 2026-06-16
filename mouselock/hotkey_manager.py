import keyboard

from mouselock.settings_store import load

_callbacks = None


def validate_hotkey(hotkey):
    hotkey = hotkey.strip().lower()
    if not hotkey:
        return False, "Hotkey cannot be empty."
    try:
        keyboard.parse_hotkey(hotkey)
    except (ValueError, KeyError):
        return False, f'"{hotkey}" is not a valid key combination.'
    return True, ""


def _expected_hotkey_names():
    settings = load()
    return (settings["select_hotkey"], settings["toggle_hotkey"], "esc")


def _listener_healthy():
    listener = keyboard._listener
    if not listener.listening:
        return False
    for attr in ("listening_thread", "processing_thread"):
        thread = getattr(listener, attr, None)
        if thread is not None and not thread.is_alive():
            return False
    return True


def _reset_dead_listener():
    listener = keyboard._listener
    if not listener.listening:
        return
    for attr in ("listening_thread", "processing_thread"):
        thread = getattr(listener, attr, None)
        if thread is not None and not thread.is_alive():
            listener.listening = False
            return


def hotkeys_are_registered():
    if _callbacks is None:
        return False
    if not _listener_healthy():
        return False
    registered = keyboard._hotkeys
    return all(name in registered for name in _expected_hotkey_names())


def ensure_hotkeys():
    if hotkeys_are_registered():
        return False
    if _callbacks is None:
        return False
    _reset_dead_listener()
    select_cb, toggle_cb, cancel_cb = _callbacks
    apply_hotkeys(select_cb, toggle_cb, cancel_cb)
    return True


def apply_hotkeys(select_cb, toggle_cb, cancel_cb):
    global _callbacks
    _callbacks = (select_cb, toggle_cb, cancel_cb)
    settings = load()
    keyboard.unhook_all()
    keyboard.add_hotkey(settings["select_hotkey"], select_cb)
    keyboard.add_hotkey(settings["toggle_hotkey"], toggle_cb)
    keyboard.add_hotkey("esc", cancel_cb)
    return settings
