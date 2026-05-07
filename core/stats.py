from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date

from .config import CONFIG_DIR

STATS_FILE = CONFIG_DIR / "stats.json"
_WORD_RE = re.compile(r"\b[\w'-]+\b", flags=re.UNICODE)


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


@dataclass
class StatsData:
    total_words: int = 0
    today_words: int = 0
    today_date: str = ""


class Stats:
    def __init__(self):
        self._data = StatsData()
        self._load()

    @property
    def total(self) -> int:
        self._roll_day()
        return self._data.total_words

    @property
    def today(self) -> int:
        self._roll_day()
        return self._data.today_words

    def add_text(self, text: str) -> int:
        words = count_words(text)
        if words <= 0:
            return 0
        self._roll_day()
        self._data.total_words += words
        self._data.today_words += words
        self._save()
        return words

    def _roll_day(self) -> None:
        today = date.today().isoformat()
        if self._data.today_date != today:
            self._data.today_date = today
            self._data.today_words = 0

    def _load(self) -> None:
        if not STATS_FILE.exists():
            self._data.today_date = date.today().isoformat()
            return
        try:
            raw = json.loads(STATS_FILE.read_text(encoding="utf-8"))
            self._data = StatsData(
                total_words=int(raw.get("total_words", 0)),
                today_words=int(raw.get("today_words", 0)),
                today_date=str(raw.get("today_date", "")),
            )
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            self._data = StatsData(today_date=date.today().isoformat())

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(
            json.dumps(asdict(self._data), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
