import sys
from pathlib import Path

import pystray
from PIL import Image

from mouselock.settings_store import format_hotkey_label, load
from mouselock.state import root

_icon = None
_callbacks = {}


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def _on_tk(callback):
    root.after(0, callback)


def _build_menu():
    settings = load()
    select_label = f"Select area ({format_hotkey_label(settings['select_hotkey'])})"
    toggle_label = f"Toggle lock ({format_hotkey_label(settings['toggle_hotkey'])})"

    return pystray.Menu(
        pystray.MenuItem(
            select_label,
            lambda icon, item: _on_tk(_callbacks["on_select"]),
            default=True,
        ),
        pystray.MenuItem(
            toggle_label,
            lambda icon, item: _on_tk(_callbacks["on_toggle"]),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Settings",
            lambda icon, item: _on_tk(_callbacks["on_settings"]),
        ),
        pystray.MenuItem(
            "Exit",
            lambda icon, item: _on_tk(_callbacks["on_exit"]),
        ),
    )


def refresh_menu():
    if _icon is not None:
        _icon.menu = _build_menu()


def setup_tray(on_select, on_toggle, on_settings, on_exit):
    global _icon

    _callbacks["on_select"] = on_select
    _callbacks["on_toggle"] = on_toggle
    _callbacks["on_settings"] = on_settings
    _callbacks["on_exit"] = on_exit

    image = Image.open(resource_path("assets", "icon.ico"))
    _icon = pystray.Icon("mouselock", image, "Mouse Lock", _build_menu())
    _icon.run_detached()
    return True


def remove_tray():
    global _icon

    icon = _icon
    _icon = None
    _callbacks.clear()
    if icon is not None:
        icon.stop()
