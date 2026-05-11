"""Toggle Windows autostart via the per-user Run registry key.

We deliberately target HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
so no admin rights are needed and the entry follows the user across machines
with sync."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger("typestream.autostart")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TypeStream"


def _exe_path() -> str:
    """Path that should be launched on startup. In a PyInstaller-frozen build
    sys.executable points at the bundled exe; in dev it points at python.exe,
    which is still useful for testing the toggle locally."""
    return str(Path(sys.executable).resolve())


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        log.debug("Reading autostart registry value failed", exc_info=True)
        return False


def set_enabled(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                value = f'"{_exe_path()}"'
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, value)
                log.info("Autostart enabled: %s", value)
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                    log.info("Autostart disabled")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        log.exception("Setting autostart registry value failed")
        return False
