import json
import os
import sys
from pathlib import Path

DEFAULT_SELECT_HOTKEY = "alt+x"
DEFAULT_TOGGLE_HOTKEY = "alt+z"

_settings_cache = None


def config_path():
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", Path.home())) / "MouseLock"
    else:
        base = Path(__file__).resolve().parent.parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


def load():
    global _settings_cache
    if _settings_cache is not None:
        return dict(_settings_cache)

    path = config_path()
    data = {
        "select_hotkey": DEFAULT_SELECT_HOTKEY,
        "toggle_hotkey": DEFAULT_TOGGLE_HOTKEY,
    }
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            data.update({k: v for k, v in stored.items() if k in data and isinstance(v, str)})
        except (json.JSONDecodeError, OSError):
            pass

    _settings_cache = dict(data)
    return dict(data)


def save(select_hotkey, toggle_hotkey):
    global _settings_cache
    data = {
        "select_hotkey": select_hotkey.strip().lower(),
        "toggle_hotkey": toggle_hotkey.strip().lower(),
    }
    config_path().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _settings_cache = dict(data)
    return data


def format_hotkey_label(hotkey):
    return "+".join(part.capitalize() for part in hotkey.split("+"))
