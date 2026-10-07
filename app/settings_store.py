"""Persistence for app settings and per-session command history."""
import json
import os
from pathlib import Path

APP_DIR_NAME = "CustomCommandCenter"

DEFAULT_SETTINGS = {
    "theme": "Dark Modern",
    "font_family": "Cascadia Mono",
    "font_size": 11,
    "default_shell": "cmd",
    "autocorrect_enabled": True,
    "code_theme": "Dark+",
    "emmet_enabled": True,
    "snake_mode": "Goal",
    "snake_skin": "Mint",
}

MAX_HISTORY = 300


def get_app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _settings_path() -> Path:
    return get_app_data_dir() / "settings.json"


def _history_path(kind: str) -> Path:
    return get_app_data_dir() / f"history_{kind}.json"


def load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


def load_history(kind: str) -> list:
    path = _history_path(kind)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(kind: str, history: list) -> None:
    try:
        trimmed = history[-MAX_HISTORY:]
        with open(_history_path(kind), "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2)
    except OSError:
        pass
