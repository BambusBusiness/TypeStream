"""Run a downloaded Inno Setup installer for an in-place self-update.

Inno Setup refuses to overwrite a running executable, so we can't just spawn
the installer and expect it to succeed. We write a small VBScript helper that
waits for our process to terminate, runs the installer with silent flags,
then launches the freshly-installed TypeStream.exe. The helper deletes itself
on exit so %TEMP% doesn't accumulate stale scripts.

Why VBScript and not a .bat: a batch helper plus `subprocess.Popen(...,
CREATE_NO_WINDOW)` leaks visible console windows on Windows whenever a
sub-command inside the batch (e.g. `tasklist | find ...`) decides to attach
to a console of its own. VBScript launched via wscript.exe is windowless by
default and `WshShell.Run(..., 0, ...)` reliably hides whatever the
installer or the relaunched app might try to show.

`launch_installer_and_quit` is the only public entry point: it spawns the
helper, returns True if the spawn succeeded, and leaves the caller to drive
its own shutdown so the Qt event loop can finish closing windows cleanly
before the helper times out waiting for our PID to die.
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

# VBScript helper:
#  - waits up to ~30s for the running TypeStream.exe (PID {pid}) to exit
#  - runs the installer with /VERYSILENT
#  - relaunches the freshly-installed app (unless suppressed)
#  - deletes itself
# `WshShell.Run(cmd, 0, True)` runs hidden + synchronously. We use that
# for the installer (we want to wait for it) and `Run(cmd, 1, False)` for
# the relaunch (visible window, fire and forget).
def _vbs_string(value: str) -> str:
    """Quote `value` as a literal VBScript string: surround with double-
    quotes, double any embedded double-quote."""
    return '"' + value.replace('"', '""') + '"'


def _render_helper(*, pid: int, installer: str, app_exe: str | None) -> str:
    """Build the .vbs helper source. Kept as a function (rather than a
    string template) so VBScript's own double-quote escaping stays
    readable; embedding a triple-double-quote inside a Python triple-
    quoted string just closes the Python string early."""
    # The string passed to WshShell.Run is a Windows command line: the exe
    # path itself needs to be wrapped in literal double-quotes so paths
    # with spaces aren't split. `_vbs_string` then escapes those quotes
    # for the surrounding VBScript literal.
    installer_cmd = f'"{installer}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL'
    installer_q = _vbs_string(installer_cmd)
    restart_line = (
        f"sh.Run {_vbs_string(chr(34) + app_exe + chr(34))}, 1, False"
        if app_exe is not None
        else "' no restart requested"
    )
    return "\n".join([
        f"' TypeStream auto-update helper - generated {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "Option Explicit",
        "Dim sh, fso, tries, stillRunning, wmi, items",
        'Set sh = CreateObject("WScript.Shell")',
        'Set fso = CreateObject("Scripting.FileSystemObject")',
        "",
        "tries = 0",
        "Do",
        "    stillRunning = False",
        "    On Error Resume Next",
        '    Set wmi = GetObject("winmgmts:\\\\.\\root\\cimv2")',
        f'    Set items = wmi.ExecQuery("Select ProcessId from Win32_Process Where ProcessId = {pid}")',
        "    If Err.Number = 0 Then",
        "        If items.Count > 0 Then stillRunning = True",
        "    End If",
        "    Err.Clear",
        "    On Error Goto 0",
        "    If Not stillRunning Then Exit Do",
        "    WScript.Sleep 1000",
        "    tries = tries + 1",
        "    If tries >= 30 Then Exit Do",
        "Loop",
        "",
        f"sh.Run {installer_q}, 0, True",
        restart_line,
        "",
        "On Error Resume Next",
        "fso.DeleteFile WScript.ScriptFullName, True",
        "",
    ])


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
    if the user explicitly does not want the app to come back up.
    """
    if not installer.exists():
        log.warning("Installer not found: %s", installer)
        return False
    if not can_self_install():
        log.info("Self-install skipped (frozen=%s platform=%s)", _is_frozen(), sys.platform)
        return False

    app_exe = str(Path(sys.executable)) if restart else None
    helper_path = Path(tempfile.gettempdir()) / f"typestream_update_{os.getpid()}.vbs"
    helper_path.write_text(
        _render_helper(pid=os.getpid(), installer=str(installer), app_exe=app_exe),
        encoding="ascii",
    )

    try:
        # wscript.exe runs .vbs without a console window — no flags needed.
        # We still pipe stdio to NUL so nothing weird leaks back.
        subprocess.Popen(
            ["wscript.exe", str(helper_path)],
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
