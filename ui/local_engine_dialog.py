from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
)

from core import local_engine

log = logging.getLogger("typestream.local_engine.ui")


class _InstallWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, kind: str):
        super().__init__()
        self._kind = kind

    def run(self) -> None:
        try:
            local_engine.install(kind=self._kind, progress=self.progress.emit)
            self.finished.emit(True, "")
        except Exception as e:
            log.exception("Local engine install failed (kind=%s)", self._kind)
            self.finished.emit(False, str(e))


class LocalEngineInstallDialog(QDialog):
    def __init__(self, kind: str = "whisper", parent=None):
        super().__init__(parent)
        self._kind = kind
        spec = local_engine.ENGINES[kind]
        self.setWindowTitle(f"{spec.label} installieren")
        self.setMinimumWidth(540)
        self.setModal(True)

        intro = QLabel(
            f"{spec.install_note}\n\n"
            "Die Installation läuft in dein Benutzerverzeichnis — keine Daten "
            "verlassen deinen Rechner. Das kann mehrere Minuten dauern."
        )
        intro.setWordWrap(True)

        self._status = QLabel("Bereit zur Installation.")
        self._status.setProperty("role", "muted")
        self._status.setWordWrap(True)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(180)
        self._log_view.setVisible(False)
        self._log_view.setPlaceholderText("pip-Output erscheint hier während der Installation …")

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._install_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self._install_btn is not None:
            self._install_btn.setText("Installieren")
            self._install_btn.setProperty("role", "primary")
        self._cancel_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if self._cancel_btn is not None:
            self._cancel_btn.setText("Schließen")
        self._buttons.accepted.connect(self._start_install)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 24)
        layout.setSpacing(14)
        layout.addWidget(intro)
        layout.addWidget(self._status)
        layout.addWidget(self._progress)
        layout.addWidget(self._log_view, 1)
        layout.addWidget(self._buttons)

        self._thread: QThread | None = None
        self._worker: _InstallWorker | None = None
        self._success = False

    def was_successful(self) -> bool:
        return self._success

    def _start_install(self) -> None:
        if self._thread is not None:
            return
        if self._install_btn is not None:
            self._install_btn.setEnabled(False)
        if self._cancel_btn is not None:
            self._cancel_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._log_view.setVisible(True)
        self._log_view.clear()
        self._status.setText("Starte Installation …")
        self.adjustSize()

        self._thread = QThread(self)
        self._worker = _InstallWorker(self._kind)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _on_progress(self, msg: str) -> None:
        self._status.setText(msg if len(msg) < 120 else msg[:117] + "…")
        self._log_view.appendPlainText(msg)
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, ok: bool, error: str) -> None:
        self._success = ok
        self._progress.setVisible(False)
        if ok:
            self._status.setText("Installation abgeschlossen.")
            if self._cancel_btn is not None:
                self._cancel_btn.setEnabled(True)
                self._cancel_btn.setText("Schließen")
            if self._install_btn is not None:
                self._install_btn.setVisible(False)
        else:
            self._status.setText("Installation fehlgeschlagen.")
            self._log_view.appendPlainText("")
            self._log_view.appendPlainText(f"FEHLER: {error}")
            sb = self._log_view.verticalScrollBar()
            sb.setValue(sb.maximum())
            if self._install_btn is not None:
                self._install_btn.setEnabled(True)
                self._install_btn.setText("Erneut versuchen")
            if self._cancel_btn is not None:
                self._cancel_btn.setEnabled(True)

    def _cleanup(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
