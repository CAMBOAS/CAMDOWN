#!/usr/bin/env python3
"""Shared, portable user settings for the downloader (CLI, GUI, and web UI).

Settings are stored in config.json next to this file. That file is
per-user/per-machine (git-ignored) so cloning this project on another
computer never carries over someone else's folder paths.
"""

import json
import sys
from pathlib import Path


def get_app_root() -> Path:
    """Writable app folder: the .exe's own folder when frozen, else this file's folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


PROJECT_ROOT = get_app_root()
CONFIG_PATH = PROJECT_ROOT / "config.json"

DEFAULTS = {
    "output_dir": "downloads",
    "quality": "1080",
}


def load_config() -> dict:
    config = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        try:
            config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(**updates) -> None:
    config = load_config()
    config.update({k: v for k, v in updates.items() if v is not None})
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_output_dir(output_dir: str | None = None) -> Path:
    """Resolve a stored/relative output dir against the project root, absolute paths pass through."""
    value = output_dir or load_config()["output_dir"]
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
