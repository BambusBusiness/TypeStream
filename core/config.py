from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Literal

APP_NAME = "TypeStream"
APP_DATA = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
CONFIG_DIR = APP_DATA / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

RecordMode = Literal["ptt", "toggle"]
Theme = Literal["dark", "light", "system"]


@dataclass
class Config:
    api_key: str = ""
    model: str = "gpt-4o-mini-transcribe"
    record_hotkey: str = "f9"
    paste_hotkey: str = "ctrl+alt+v"
    record_mode: RecordMode = "ptt"
    history_limit: int = 50
    language: str = "de"
    min_record_duration: float = 0.4
    play_sounds: bool = True
    show_overlay: bool = True
    style: str = "original"
    custom_style_prompt: str = ""
    theme: Theme = "system"

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
