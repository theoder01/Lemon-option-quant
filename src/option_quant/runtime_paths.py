# Copyright © 2026 Bo Hu. All rights reserved.
"""Centralized source and frozen-app paths; independent of working directory."""
from pathlib import Path
import sys


def resource_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def default_database_path() -> Path:
    return resource_root() / 'data' / 'options.db'


def preference_path() -> Path:
    # Keep mutable preferences outside PyInstaller's bundled resources.
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else resource_root()
    return base / 'data' / 'gui_preferences.json'
