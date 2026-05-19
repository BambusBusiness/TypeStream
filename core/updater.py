from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.version import GITHUB_REPO, __version__

log = logging.getLogger("typestream.updater")

RELEASES_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_BY_TAG_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{{tag}}"
)
RELEASES_FALLBACK_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"TypeStream-UpdateCheck/{__version__}"
TIMEOUT_SECONDS = 8.0
DOWNLOAD_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    current_version: str
    download_url: str  # Release HTML page (browser fallback)
    installer_url: str  # Direct .exe download (empty when no asset attached)
    installer_filename: str
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


def _pick_installer_asset(assets: list) -> tuple[str, str]:
    """Return (download_url, filename) for the first .exe asset, or
    ("","") if the release has none."""
    if not isinstance(assets, list):
        return "", ""
    for a in assets:
        if not isinstance(a, dict):
            continue
        name = (a.get("name") or "").lower()
        url = a.get("browser_download_url") or ""
        if name.endswith(".exe") and url:
            return url, a.get("name") or ""
    return "", ""


def _release_from_payload(data: dict, current: str) -> Optional[UpdateInfo]:
    latest_tag = (data.get("tag_name") or "").strip()
    if not latest_tag:
        return None
    latest = latest_tag.lstrip("vV")
    installer_url, installer_filename = _pick_installer_asset(
        data.get("assets") or []
    )
    return UpdateInfo(
        latest_version=latest,
        current_version=current,
        download_url=data.get("html_url") or RELEASES_FALLBACK_URL,
        installer_url=installer_url,
        installer_filename=installer_filename,
        release_name=data.get("name") or latest,
        release_notes=data.get("body") or "",
    )


def _fetch_release(url: str) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
        log.info("Release fetch failed (%s): %s", url, e)
        return None


def check_for_update(current: str = __version__) -> Optional[UpdateInfo]:
    """Query GitHub for the latest release. Returns None if up-to-date or
    if the network is unreachable. Never raises."""
    data = _fetch_release(RELEASES_LATEST_URL)
    if data is None:
        return None
    info = _release_from_payload(data, current)
    if info is None:
        return None
    if not is_newer(info.latest_version, current):
        log.info("Up to date (current=%s, latest=%s)", current, info.latest_version)
        return None
    return info


def fetch_release(tag: str, current: str = __version__) -> Optional[UpdateInfo]:
    """Look up a specific release by tag — used by the downgrade flow to
    fetch the previous release's installer URL. Accepts both "0.1.0" and
    "v0.1.0"."""
    tag_clean = tag.strip()
    if not tag_clean:
        return None
    if not tag_clean.startswith(("v", "V")):
        tag_clean = f"v{tag_clean}"
    data = _fetch_release(RELEASE_BY_TAG_URL.format(tag=tag_clean))
    if data is None:
        return None
    return _release_from_payload(data, current)


def download_installer(
    url: str,
    dest: Path,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """Download `url` into `dest` atomically.

    Streams in 64KB chunks and renames into place only after the download
    finishes — interrupted downloads never leave a partial .exe at `dest`.
    Returns True on success, False otherwise (network error / disk error /
    empty body). Errors are logged."""
    if not url:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = Path(tempfile.mkstemp(prefix="typestream_dl_", dir=dest.parent)[1])
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SECONDS) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            written = 0
            with tmp.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
                    if on_progress is not None:
                        try:
                            on_progress(written, total)
                        except Exception:
                            log.debug("progress callback raised", exc_info=True)
        if written == 0:
            log.warning("Empty download from %s", url)
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, dest)
        log.info("Installer downloaded: %s (%d bytes)", dest, written)
        return True
    except (urllib.error.URLError, OSError) as e:
        log.exception("Installer download failed: %s", e)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
