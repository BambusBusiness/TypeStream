from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime

from .config import CONFIG_DIR, HISTORY_FILE


@dataclass
class HistoryEntry:
    text: str
    timestamp: str
    cloud_seconds: float | None = None
    local_seconds: float | None = None
    engine_used: str | None = None
    timings: dict[str, float] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        text: str,
        *,
        cloud_seconds: float | None = None,
        local_seconds: float | None = None,
        engine_used: str | None = None,
        timings: dict[str, float] | None = None,
    ) -> "HistoryEntry":
        return cls(
            text=text,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            cloud_seconds=cloud_seconds,
            local_seconds=local_seconds,
            engine_used=engine_used,
            timings=dict(timings) if timings else {},
        )

    def all_timings(self) -> dict[str, float]:
        """Merge legacy fields with new timings dict for unified access."""
        merged: dict[str, float] = {}
        if self.cloud_seconds is not None:
            merged["openai"] = self.cloud_seconds
        if self.local_seconds is not None:
            merged.setdefault("whisper", self.local_seconds)
        merged.update(self.timings or {})
        return merged

    def winner(self) -> str | None:
        if self.cloud_seconds is None or self.local_seconds is None:
            return None
        return "openai" if self.cloud_seconds <= self.local_seconds else "local"


class History:
    def __init__(self, limit: int = 50):
        self._limit = max(1, limit)
        self._entries: list[HistoryEntry] = []
        self._load()

    def add(
        self,
        text: str,
        *,
        cloud_seconds: float | None = None,
        local_seconds: float | None = None,
        engine_used: str | None = None,
        timings: dict[str, float] | None = None,
    ) -> HistoryEntry:
        entry = HistoryEntry.new(
            text,
            cloud_seconds=cloud_seconds,
            local_seconds=local_seconds,
            engine_used=engine_used,
            timings=timings,
        )
        self._entries.insert(0, entry)
        self._enforce_limit()
        self._save()
        return entry

    def latest(self) -> HistoryEntry | None:
        return self._entries[0] if self._entries else None

    def all(self) -> list[HistoryEntry]:
        return list(self._entries)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._entries):
            del self._entries[index]
            self._save()

    def clear(self) -> None:
        self._entries = []
        self._save()

    def set_limit(self, limit: int) -> None:
        self._limit = max(1, limit)
        if self._enforce_limit():
            self._save()

    def _enforce_limit(self) -> bool:
        if len(self._entries) > self._limit:
            self._entries = self._entries[: self._limit]
            return True
        return False

    def _load(self) -> None:
        if not HISTORY_FILE.exists():
            return
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            valid = {f.name for f in fields(HistoryEntry)}
            self._entries = [
                HistoryEntry(**{k: v for k, v in e.items() if k in valid})
                for e in data
            ][: self._limit]
        except (json.JSONDecodeError, OSError, TypeError):
            self._entries = []

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps([asdict(e) for e in self._entries], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
