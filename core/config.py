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
Engine = Literal["openai", "local"]
LocalModelSize = Literal["tiny", "base", "small"]
UiLanguage = Literal["system", "de", "en"]


@dataclass
class Config:
    engine: Engine = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini-transcribe"
    local_model_size: LocalModelSize = "base"
    record_hotkey: str = "f9"
    paste_hotkey: str = "ctrl+alt+v"
    record_mode: RecordMode = "ptt"
    history_limit: int = 50
    language: str = "de"
    min_record_duration: float = 0.4
    input_device: str = ""
    play_sounds: bool = True
    beep_volume: float = 0.6
    warning_volume: float = 0.6
    show_overlay: bool = True
    autostart: bool = True
    style: str = "original"
    style_mode: str = "hint"
    refine_model: str = "gpt-4o-mini"
    custom_style_prompt: str = ""
    theme: Theme = "system"
    ui_language: UiLanguage = "system"
    benchmark_mode: bool = False
    benchmark_engine_a: str = "openai"
    benchmark_engine_b: str = "whisper"
    # Tracks the __version__ we saw on the last launch. If the running app
    # reports a different __version__, we know an install happened in between
    # and remember what we just upgraded *from* in `previous_version`. The
    # Settings → Updates page exposes a one-click downgrade back to that
    # version when a release turns out to be broken.
    installed_version_seen: str = ""
    previous_version: str = ""

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
