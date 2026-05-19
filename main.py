from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    try:
        # Without an explicit AppUserModelID, Windows groups our windows under
        # the Python interpreter's taskbar entry and shows that interpreter's
        # icon — which is why our icon would otherwise look blurry/wrong on
        # the taskbar. Setting our own AUMID gives Windows a stable identity
        # to attach our HD icon to.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Otark.TypeStream"
        )
    except (AttributeError, OSError):
        pass
    try:
        import ctypes
        HIGH_PRIORITY_CLASS = 0x00000080
        ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        if not kernel32.SetPriorityClass(handle, HIGH_PRIORITY_CLASS):
            kernel32.SetPriorityClass(handle, ABOVE_NORMAL_PRIORITY_CLASS)
    except (AttributeError, OSError):
        pass
    try:
        import ctypes
        from ctypes import wintypes

        class _PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
            _fields_ = [
                ("Version", wintypes.ULONG),
                ("ControlMask", wintypes.ULONG),
                ("StateMask", wintypes.ULONG),
            ]

        _PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
        _ProcessPowerThrottling = 4
        _state = _PROCESS_POWER_THROTTLING_STATE()
        _state.Version = 1
        _state.ControlMask = _PROCESS_POWER_THROTTLING_EXECUTION_SPEED
        _state.StateMask = 0
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        kernel32.SetProcessInformation(
            handle,
            _ProcessPowerThrottling,
            ctypes.byref(_state),
            ctypes.sizeof(_state),
        )
    except (AttributeError, OSError):
        pass

LOG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "TypeStream"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "typestream.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("typestream")
from core.version import __version__
log.info("=== TypeStream startup (v%s) ===", __version__)
log.info("Python: %s", sys.version)
log.info("Log file: %s", LOG_FILE)


def excepthook(exc_type, exc_value, exc_tb):
    log.critical("UNCAUGHT EXCEPTION:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = excepthook

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from core import sounds
from ui.app import AppController
from ui.style import APP_QSS
from ui.tray import load_app_icon

SINGLE_INSTANCE_KEY = "TypeStream-SingleInstance"


def main() -> int:
    log.info("Creating QApplication")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("TypeStream")
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(APP_QSS)

    probe = QLocalSocket()
    probe.connectToServer(SINGLE_INSTANCE_KEY)
    if probe.waitForConnected(300):
        log.info("Another TypeStream instance is already running — focusing it")
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return 0

    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    instance_server = QLocalServer()
    if not instance_server.listen(SINGLE_INSTANCE_KEY):
        log.warning(
            "Single-instance server failed to listen: %s", instance_server.errorString()
        )

    log.info("Initializing audio feedback")
    sounds.init()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.error("System tray not available")
        QMessageBox.critical(
            None,
            "TypeStream",
            "System Tray ist auf diesem System nicht verfügbar.",
        )
        return 1
    log.info("System tray available")

    log.info("Constructing AppController")
    controller = AppController(app)

    def _on_second_instance() -> None:
        sock = instance_server.nextPendingConnection()
        if sock is not None:
            sock.disconnectFromServer()
        log.info("Second-instance ping received — showing main window")
        controller.show_main_window()

    instance_server.newConnection.connect(_on_second_instance)

    log.info("AppController constructed; entering event loop")
    rc = app.exec()
    log.info("Event loop exited with rc=%s", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
