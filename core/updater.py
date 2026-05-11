from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from core.version import GITHUB_REPO, __version__

log = logging.getLogger("typestream.updater")

RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_FALLBACK_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"TypeStream-UpdateCheck/{__version__}"
TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    current_version: str
    download_url: str
    release_name: str
    release_notes: str


def _parse_version(v: str) -> tuple[int, ...]:
    v = v.lstrip("vV").strip()
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", v)
    if not m:
        return (0,)
    return tuple(int(g) if g is not None else 0 for g in m.groups())


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_for_update(current: str = __version__) -> Optional[UpdateInfo]:
    """Query GitHub for the latest release.

    Returns None if no newer version exists, the network is unreachable, or
    the response is unexpected. Never raises — failures are logged at INFO."""
    req = urllib.request.Request(
        RELEASES_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
        log.info("Update check skipped: %s", e)
        return None

    latest_tag = (data.get("tag_name") or "").strip()
    if not latest_tag:
        return None
    latest = latest_tag.lstrip("vV")
    if not is_newer(latest, current):
        log.info("Up to date (current=%s, latest=%s)", current, latest)
        return None

    return UpdateInfo(
        latest_version=latest,
        current_version=current,
        download_url=data.get("html_url") or RELEASES_FALLBACK_URL,
        release_name=data.get("name") or latest,
        release_notes=data.get("body") or "",
    )
