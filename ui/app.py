from __future__ import annotations

import logging
import queue
import threading
from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog

log = logging.getLogger("typestream.app")

from core import sounds
from core.config import Config
from core.history import History
from core.hotkeys import HotkeyManager
from core.inserter import TextInserter
from core.recorder import AudioRecorder
from core.stats import Stats
from core.styles import all_styles, find_style
from core.transcriber import Transcriber
from ui.main_window import MainWindow
from ui.overlay import RecordingOverlay
from ui.settings_dialog import SettingsDialog
from ui.style import apply_card_shadow, build_qss, get_palette
from ui.tray import TrayIcon

STATE_IDLE = "idle"
STATE_RECORDING = "recording"


class AppController(QObject):
    _record_start = pyqtSignal()
    _record_stop = pyqtSignal()
    _record_toggle = pyqtSignal()
    _paste_last = pyqtSignal()
    _transcription_done = pyqtSignal(str)
    _transcription_failed = pyqtSignal(str)

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._config = Config.load()
        self._history = History(limit=self._config.history_limit)
        self._stats = Stats()
        self._recorder = AudioRecorder()
        self._transcriber = Transcriber(
            self._config.api_key,
            self._config.model,
            self._config.language,
            self._active_style_prompt(),
        )
        self._inserter = TextInserter()
        self._hotkeys = HotkeyManager()
        self._state = STATE_IDLE

        self._transcribe_queue: "queue.Queue[Path | None]" = queue.Queue()
        self._pending_count = 0
        self._pending_lock = threading.Lock()
        self._transcribe_worker = threading.Thread(
            target=self._transcribe_worker_loop,
            name="transcribe-worker",
            daemon=True,
        )
        self._transcribe_worker.start()

        self._tray = TrayIcon(self)
        self._main_window = MainWindow(self._history, self._stats)
        self._overlay = RecordingOverlay()

        self._apply_theme()
        try:
            self._app.styleHints().colorSchemeChanged.connect(
                self._on_system_color_scheme_changed
            )
        except Exception:
            log.debug("colorSchemeChanged signal not available")
        self._refresh_tray_styles()
        self._wire_signals()
        log.info("Signals wired")
        self._register_hotkeys()
        log.info("Hotkeys registered (record=%s mode=%s paste=%s)",
                 self._config.record_hotkey, self._config.record_mode, self._config.paste_hotkey)
        self._tray.show()
        log.info("Tray show() called; tray.isVisible=%s", self._tray.isVisible())

        if not self._config.api_key:
            log.info("API key missing — settings dialog will auto-open")
            QTimer.singleShot(300, self.open_settings)
        else:
            log.info("API key present")

    def _wire_signals(self) -> None:
        self._tray.open_history.connect(self.open_history)
        self._tray.open_settings.connect(self.open_settings)
        self._tray.copy_last.connect(self.copy_last)
        self._tray.quit_app.connect(self.quit)
        self._tray.style_changed.connect(self._on_style_changed)

        self._main_window.copy_requested.connect(self._on_copy_request)
        self._main_window.insert_requested.connect(self._on_insert_request)
        self._main_window.settings_requested.connect(self.open_settings)
        self._main_window.style_changed.connect(self._on_style_changed)

        q = Qt.ConnectionType.QueuedConnection
        self._record_start.connect(self._start_recording, q)
        self._record_stop.connect(self._stop_recording, q)
        self._record_toggle.connect(self._toggle_recording, q)
        self._paste_last.connect(self._paste_last_history, q)
        self._transcription_done.connect(self._on_transcription_done, q)
        self._transcription_failed.connect(self._on_transcription_failed, q)

    def _register_hotkeys(self) -> None:
        self._hotkeys.unregister_all()
        try:
            if self._config.record_mode == "ptt" and "+" not in self._config.record_hotkey:
                self._hotkeys.register_record_ptt(
                    self._config.record_hotkey,
                    self._record_start.emit,
                    self._record_stop.emit,
                )
            else:
                self._hotkeys.register_record_toggle(
                    self._config.record_hotkey,
                    self._record_toggle.emit,
                )
                if self._config.record_mode == "ptt":
                    self._tray.notify(
                        "Tastenkombination erkannt — PTT wird als Toggle behandelt.",
                        "warn",
                    )
            self._hotkeys.register_paste(self._config.paste_hotkey, self._paste_last.emit)
        except Exception as e:
            log.exception("Hotkey registration failed")
            self._tray.notify(f"Hotkey-Fehler: {e}", "error")

    def open_history(self) -> None:
        self._main_window.refresh()
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def open_settings(self) -> None:
        snapshot = replace(self._config)
        dialog = SettingsDialog(self._config, parent=self._main_window)
        dialog.changed.connect(self._apply_settings_live)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._apply_settings_live(snapshot)

    def _apply_settings_live(self, new_cfg: Config) -> None:
        prev = self._config
        if new_cfg == prev:
            return
        self._config = new_cfg
        self._config.save()
        if new_cfg.history_limit != prev.history_limit:
            self._history.set_limit(new_cfg.history_limit)
        if (
            new_cfg.api_key != prev.api_key
            or new_cfg.model != prev.model
            or new_cfg.language != prev.language
            or new_cfg.style != prev.style
            or new_cfg.custom_style_prompt != prev.custom_style_prompt
        ):
            self._transcriber.update(
                new_cfg.api_key,
                new_cfg.model,
                new_cfg.language,
                self._active_style_prompt(),
            )
        if new_cfg.custom_style_prompt != prev.custom_style_prompt:
            self._refresh_tray_styles()
        if (
            new_cfg.record_hotkey != prev.record_hotkey
            or new_cfg.record_mode != prev.record_mode
            or new_cfg.paste_hotkey != prev.paste_hotkey
        ):
            self._register_hotkeys()
        if new_cfg.theme != prev.theme:
            self._apply_theme()

    def _apply_theme(self) -> None:
        palette = get_palette(self._resolved_theme())
        self._app.setStyleSheet(build_qss(palette))
        self._overlay.apply_palette(palette)
        apply_card_shadow(self._main_window.list_widget(), palette)

    def _resolved_theme(self) -> str:
        if self._config.theme == "system":
            return self._detect_system_theme()
        return self._config.theme

    def _detect_system_theme(self) -> str:
        try:
            scheme = self._app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "light"
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
        except Exception:
            log.debug("colorScheme() not available")
        return "dark"

    def _on_system_color_scheme_changed(self, _scheme) -> None:
        if self._config.theme == "system":
            self._apply_theme()

    def _active_style_prompt(self) -> str:
        return find_style(self._config.style, self._config.custom_style_prompt).prompt

    def _refresh_tray_styles(self) -> None:
        styles = all_styles(self._config.custom_style_prompt)
        if not any(s.key == self._config.style for s in styles):
            self._config.style = "original"
            self._config.save()
            self._transcriber.set_prompt(self._active_style_prompt())
        self._tray.update_styles(styles, self._config.style)
        self._main_window.update_styles(styles, self._config.style)

    def _on_style_changed(self, key: str) -> None:
        if key == self._config.style:
            return
        self._config.style = key
        self._config.save()
        self._transcriber.set_prompt(self._active_style_prompt())
        self._tray.set_active_style(key)
        self._main_window.set_active_style(key)
        label = find_style(key, self._config.custom_style_prompt).label
        self._tray.notify(f"Stil: {label}", "info")

    def copy_last(self) -> None:
        latest = self._history.latest()
        if latest is None:
            self._tray.notify("Kein Text im Verlauf.", "warn")
            return
        self._inserter.copy_to_clipboard(latest.text)
        self._tray.notify("Letzter Text in Zwischenablage kopiert.", "info")

    def quit(self) -> None:
        self._hotkeys.unregister_all()
        try:
            if self._recorder.is_recording():
                self._recorder.stop()
        except Exception:
            pass
        try:
            self._transcribe_queue.put_nowait(None)
        except Exception:
            pass
        self._tray.hide()
        self._app.quit()

    def _update_tray_state(self) -> None:
        if self._state == STATE_RECORDING:
            self._tray.set_state_recording()
        elif self._pending_count > 0:
            self._tray.set_state_busy()
        else:
            self._tray.set_state_idle()

    def _notify_silent(self, text: str, level: str = "warn") -> None:
        log.info("notify (silent) [%s] %s", level, text)
        if self._config.show_overlay and self._state != STATE_RECORDING:
            self._overlay.show_message(text, level)

    def _start_recording(self) -> None:
        if self._state != STATE_IDLE:
            return
        if not self._config.api_key:
            self._tray.notify("Kein API-Key gesetzt — bitte Einstellungen öffnen.", "error")
            return
        try:
            self._recorder.start()
        except Exception as e:
            self._tray.notify(f"Aufnahme-Start fehlgeschlagen: {e}", "error")
            return
        self._state = STATE_RECORDING
        self._update_tray_state()
        if self._config.show_overlay:
            self._overlay.show_recording()
        if self._config.play_sounds:
            sounds.play_start()

    def _stop_recording(self) -> None:
        if self._state != STATE_RECORDING:
            return
        try:
            wav = self._recorder.stop(min_duration_s=self._config.min_record_duration)
        except Exception as e:
            self._state = STATE_IDLE
            if self._config.show_overlay:
                self._overlay.hide_with_fade()
            self._update_tray_state()
            self._tray.notify(f"Aufnahme-Stop fehlgeschlagen: {e}", "error")
            return
        if self._config.play_sounds:
            sounds.play_stop()
        self._state = STATE_IDLE
        if self._config.show_overlay:
            self._overlay.hide_with_fade()
        if wav is None:
            self._update_tray_state()
            self._notify_silent(
                f"Aufnahme zu kurz (< {self._config.min_record_duration:.1f}s)",
                "warn",
            )
            return
        with self._pending_lock:
            self._pending_count += 1
        self._update_tray_state()
        self._transcribe_queue.put(wav)

    def _toggle_recording(self) -> None:
        if self._state == STATE_IDLE:
            self._start_recording()
        elif self._state == STATE_RECORDING:
            self._stop_recording()

    def _transcribe_worker_loop(self) -> None:
        while True:
            wav = self._transcribe_queue.get()
            if wav is None:
                return
            try:
                text = self._transcriber.transcribe(wav)
                self._transcription_done.emit(text)
            except Exception as e:
                log.exception("Transcription failed")
                self._transcription_failed.emit(str(e))
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except Exception:
                    pass

    def _on_transcription_done(self, text: str) -> None:
        with self._pending_lock:
            if self._pending_count > 0:
                self._pending_count -= 1
        self._update_tray_state()
        if not text:
            self._notify_silent("Keine Sprache erkannt", "warn")
            return
        self._history.add(text)
        self._stats.add_text(text)
        if self._main_window.isVisible():
            self._main_window.refresh()
        if not self._inserter.insert_at_cursor(text):
            self._notify_silent(
                "Auto-Einfügen fehlgeschlagen — Text in Zwischenablage",
                "warn",
            )

    def _on_transcription_failed(self, error: str) -> None:
        with self._pending_lock:
            if self._pending_count > 0:
                self._pending_count -= 1
        self._update_tray_state()
        self._notify_silent(f"Transkription fehlgeschlagen: {error}", "error")

    def _paste_last_history(self) -> None:
        latest = self._history.latest()
        if latest is None:
            self._tray.notify("Kein Text im Verlauf.", "warn")
            return
        QTimer.singleShot(80, lambda: self._inserter.insert_at_cursor(latest.text))

    def _on_copy_request(self, text: str) -> None:
        self._inserter.copy_to_clipboard(text)
        self._tray.notify("In Zwischenablage kopiert.", "info")

    def _on_insert_request(self, text: str) -> None:
        self._main_window.hide()
        QTimer.singleShot(120, lambda: self._inserter.insert_at_cursor(text))
