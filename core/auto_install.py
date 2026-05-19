"""Run a downloaded Inno Setup installer for an in-place self-update.

Inno Setup refuses to overwrite a running executable, so we can't just spawn
the installer and expect it to succeed. We write a small batch helper that
waits a few seconds for our process to terminate, runs the installer with
silent flags, then launches the freshly-installed TypeStream.exe. The batch
deletes itself on exit so /TEMP doesn't accumulate stale helpers.

`launch_installer_and_quit` is the only public entry point: it spawns the
helper detached from the current console, returns True if the spawn
succeeded, and leaves the caller to drive its own shutdown (so the Qt event
loop can finish closing windows cleanly before the wait timer elapses).
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

log = logging.getLogger("typestream.auto_install")

_HELPER_TEMPLATE = """@echo off
setlocal
rem TypeStream auto-update helper - generated {timestamp}
rem Wait for the running TypeStream.exe (PID {pid}) to exit, then install
rem the new version and start it again.

set TARGET_PID={pid}
set WAIT_TRIES=0
:waitloop
tasklist /FI "PID eq %TARGET_PID%" 2>nul | find "%TARGET_PID%" >nul
if errorlevel 1 goto installed
set /a WAIT_TRIES+=1
if %WAIT_TRIES% GEQ 30 goto installed
timeout /T 1 /NOBREAK >nul
goto waitloop

:installed
"{installer}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL
{post_run}
(goto) 2>nul & del "%~f0"
"""


def _is_frozen() -> bool:
    """True when running from the PyInstaller bundle — only then does
    self-update make sense. From a dev checkout there's no exe to replace."""
    return bool(getattr(sys, "frozen", False))


def can_self_install() -> bool:
    return sys.platform == "win32" and _is_frozen()


def launch_installer_and_quit(installer: Path, *, restart: bool = True) -> bool:
    """Spawn the update helper. Returns True if the helper was successfully
    launched — the caller should then quit the Qt app so the helper can
    take over.

    `restart`: True for normal updates (start the new app afterward); False
    if the user explicitly does not want the app to come back up. In
    practice we always pass True.
    """
    if not installer.exists():
        log.warning("Installer not found: %s", installer)
        return False
    if not can_self_install():
        log.info("Self-install skipped (frozen=%s platform=%s)", _is_frozen(), sys.platform)
        return False

    app_exe = Path(sys.executable)
    post_run = f'start "" "{app_exe}"' if restart else "rem no restart"
    helper_path = Path(tempfile.gettempdir()) / f"typestream_update_{os.getpid()}.bat"
    helper_path.write_text(
        _HELPER_TEMPLATE.format(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            pid=os.getpid(),
            installer=str(installer),
            post_run=post_run,
        ),
        encoding="ascii",
    )

    try:
        # DETACHED_PROCESS so the helper survives our exit, CREATE_NO_WINDOW
        # so no cmd.exe flashes up. CREATE_NEW_PROCESS_GROUP isolates it
        # from Ctrl-C in any inherited console.
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        subprocess.Popen(
            ["cmd.exe", "/c", str(helper_path)],
            creationflags=flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Update helper spawned: %s (installer=%s)", helper_path, installer)
        return True
    except OSError as e:
        log.exception("Failed to spawn update helper: %s", e)
        try:
            helper_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
