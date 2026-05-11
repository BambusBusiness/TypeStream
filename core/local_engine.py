from __future__ import annotations

import contextlib
import importlib
import io
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, TextIO

log = logging.getLogger("typestream.local_engine")

LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
RUNTIME_DIR = LOCAL_APP_DATA / "TypeStream" / "runtime"
SITE_PACKAGES = RUNTIME_DIR / "site-packages"

EngineKind = Literal["whisper"]


@dataclass(frozen=True)
class EngineSpec:
    kind: EngineKind
    label: str
    import_name: str
    pip_specs: tuple[str, ...]
    extra_pip_args: tuple[str, ...]
    size_hint_mb: int
    install_note: str


ENGINES: dict[str, EngineSpec] = {
    "whisper": EngineSpec(
        kind="whisper",
        label="Faster-Whisper",
        import_name="faster_whisper",
        pip_specs=("faster-whisper",),
        extra_pip_args=(),
        size_hint_mb=300,
        install_note=(
            "Faster-Whisper (~250 MB Download). Läuft auf CPU, gute Qualität "
            "für viele Sprachen inkl. Deutsch."
        ),
    ),
}


class LocalEngineNotInstalled(RuntimeError):
    pass


def _add_runtime_to_syspath() -> None:
    if SITE_PACKAGES.exists():
        sp = str(SITE_PACKAGES)
        if sp not in sys.path:
            sys.path.insert(0, sp)
            log.debug("Added %s to sys.path", sp)


_add_runtime_to_syspath()


def is_installed(kind: EngineKind = "whisper") -> bool:
    _add_runtime_to_syspath()
    spec = ENGINES[kind]
    try:
        importlib.import_module(spec.import_name)
        return True
    except ImportError:
        return False


class _TeeStream:
    """Write to original stream AND a buffer; forward newline-terminated chunks
    to an optional progress callback so the UI can show pip output live.

    Pip probes stdout/stderr for several stream attributes (isatty, encoding,
    fileno, …) — we delegate unknown attribute access to the underlying stream
    and explicitly report isatty()=False so pip skips spinner/progress-bar
    rendering that would garble our captured output."""

    def __init__(
        self,
        original: TextIO,
        buffer: io.StringIO,
        progress: Callable[[str], None] | None,
    ):
        self._original = original
        self._buffer = buffer
        self._progress = progress
        self._line_buf = ""

    def write(self, data: str) -> int:
        try:
            self._original.write(data)
        except Exception:
            pass
        self._buffer.write(data)
        if self._progress:
            self._line_buf += data
            while "\n" in self._line_buf:
                line, self._line_buf = self._line_buf.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        self._progress(line)
                    except Exception:
                        pass
        return len(data)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._original, name)


def install(
    kind: EngineKind = "whisper",
    progress: Callable[[str], None] | None = None,
) -> None:
    """Install the chosen local engine into a user-writable runtime dir."""
    spec = ENGINES[kind]
    SITE_PACKAGES.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(
            f"Installiere {spec.label} ({', '.join(spec.pip_specs)}) nach "
            f"{SITE_PACKAGES} …"
        )
    try:
        from pip._internal.cli.main import main as pip_main
    except ImportError as e:
        raise RuntimeError(
            "pip ist nicht verfügbar — kann Engine nicht installieren."
        ) from e

    args = [
        "install",
        "--target", str(SITE_PACKAGES),
        "--upgrade",
        "--no-warn-script-location",
        "--disable-pip-version-check",
        *spec.extra_pip_args,
        *spec.pip_specs,
    ]
    log.info("pip install args (engine=%s): %s", kind, args)

    buffer = io.StringIO()
    tee_out = _TeeStream(sys.stdout, buffer, progress)
    tee_err = _TeeStream(sys.stderr, buffer, progress)
    with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
        try:
            code = pip_main(args)
        except SystemExit as e:
            code = int(e.code) if isinstance(e.code, int) else 1

    output = buffer.getvalue()
    log.info("pip install output (engine=%s, exit=%s):\n%s", kind, code, output)

    if code != 0:
        tail = "\n".join(output.strip().splitlines()[-25:])
        raise RuntimeError(
            f"pip install fehlgeschlagen (Exit-Code {code}).\n\n"
            f"Letzte Zeilen aus pip:\n{tail}"
        )
    _add_runtime_to_syspath()
    importlib.invalidate_caches()
    if progress:
        progress("Installation abgeschlossen.")
