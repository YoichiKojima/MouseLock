import sys
from pathlib import Path

import pystray
from PIL import Image

from mouselock.state import root

_icon = None


def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def _on_tk(callback):
    root.after(0, callback)


def setup_tray(on_select, on_toggle, on_exit):
    global _icon

    image = Image.open(resource_path("assets", "icon.ico"))
    menu = pystray.Menu(
        pystray.MenuItem(
            "Select area",
            lambda icon, item: _on_tk(on_select),
            default=True,
        ),
        pystray.MenuItem(
            "Toggle lock",
            lambda icon, item: _on_tk(on_toggle),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Exit",
            lambda icon, item: _on_tk(on_exit),
        ),
    )

    _icon = pystray.Icon("mouselock", image, "Mouse Lock", menu)
    _icon.run_detached()
    return True


def remove_tray():
    global _icon

    icon = _icon
    _icon = None
    if icon is not None:
        icon.stop()
