# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

"""GUI-only translation and preferences; analysis never imports this module."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import sqlite3

from option_quant.gui_strings import LANGUAGES, STRINGS


@dataclass(frozen=True)
class Message:
    key: str
    values: dict = field(default_factory=dict)


@dataclass(frozen=True)
class JoinedMessages:
    messages: tuple
    separator_key: str | None = None


def message(key: str, **values) -> Message:
    return Message(key, values)


class Translator:
    def __init__(self, language: str = "en"):
        self.language = language if language in LANGUAGES else "en"

    def render(self, value) -> str:
        if isinstance(value, JoinedMessages):
            separator = self.render(message(value.separator_key)) if value.separator_key else "\n"
            return separator.join(self.render(item) for item in value.messages)
        if not isinstance(value, Message):
            return str(value)
        translations = STRINGS[value.key]
        template = translations.get(self.language, translations["en"])
        values = {key: self.render(item) if isinstance(item, (Message, JoinedMessages)) else item
                  for key, item in value.values.items()}
        return template.format(**values)


# Existing analysis APIs return English prose. Translate it only at the GUI
# boundary, keeping those APIs independent of the display language.
_ENGLISH_KEYS = {translations["en"]: key for key, translations in STRINGS.items()}


def canonical_message(text: str):
    key = _ENGLISH_KEYS.get(text)
    return message(key) if key else text


def error_message(error: Exception) -> Message:
    text = str(error)
    if text in _ENGLISH_KEYS:
        return message(_ENGLISH_KEYS[text])
    if isinstance(error, sqlite3.Error):
        if "unable to open database file" in text:
            return message("database_open_error")
        if "no such table" in text or "no such column" in text:
            return message("database_schema_error")
    # Preserve unrecognized library/OS diagnostics rather than hiding details.
    return message("unknown_error", detail=text)


def load_language(path: Path | None) -> str:
    if path is None:
        return "en"
    try:
        data = path.read_text(encoding="utf-8")
        preferences = json.loads(data)
        language = preferences.get("language") if isinstance(preferences, dict) else None
        return language if isinstance(language, str) and language in LANGUAGES else "en"
    except (OSError, ValueError):
        return "en"


def save_language(path: Path | None, language: str) -> bool:
    if path is None:
        return True
    if language not in LANGUAGES:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"language": language}) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False
