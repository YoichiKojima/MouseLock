import json
import os
import sys
from pathlib import Path

DEFAULT_SELECT_HOTKEY = "alt+x"
DEFAULT_TOGGLE_HOTKEY = "alt+z"
DEFAULT_START_WITH_WINDOWS = False

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
        "start_with_windows": DEFAULT_START_WITH_WINDOWS,
    }
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            for key, value in stored.items():
                if key not in data:
                    continue
                if key == "start_with_windows" and isinstance(value, bool):
                    data[key] = value
                elif key in ("select_hotkey", "toggle_hotkey") and isinstance(value, str):
                    data[key] = value
        except (json.JSONDecodeError, OSError):
            pass

    _settings_cache = dict(data)
    return dict(data)


def save(select_hotkey, toggle_hotkey, start_with_windows=False):
    global _settings_cache
    data = {
        "select_hotkey": select_hotkey.strip().lower(),
        "toggle_hotkey": toggle_hotkey.strip().lower(),
        "start_with_windows": bool(start_with_windows),
    }
    config_path().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _settings_cache = dict(data)
    return data


def format_hotkey_label(hotkey):
    return "+".join(part.capitalize() for part in hotkey.split("+"))
