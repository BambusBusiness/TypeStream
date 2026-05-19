from __future__ import annotations

import logging
import queue
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

log = logging.getLogger("typestream.app")

from core import (
    auto_install,
    autostart,
    hallucinations,
    local_engine,
    refiner,
    sounds,
    updater,
)
from core.config import APP_DATA, Config
from core.history import History
from core.hotkeys import HotkeyManager
from core.inserter import TextInserter
from core.recorder import AudioRecorder
from core.stats import Stats
from core.styles import all_styles, find_style
from core.transcriber import Transcriber
from core.updater import UpdateInfo
from core.version import __version__
from ui.main_window import MainWindow
from ui.overlay import RecordingOverlay
from ui.style import apply_card_shadow, build_qss, get_palette
from ui.tray import TrayIcon

STATE_IDLE = "idle"
STATE_RECORDING = "recording"

UPDATE_CHECK_DELAY_MS = 8000
UPDATE_CACHE_DIR = APP_DATA / "TypeStream" / "updates"


class _UpdateCheckWorker(QObject):
    finished = pyqtSignal(object)  # UpdateInfo | None

    def run(self) -> None:
        info = updater.check_for_update()
        self.finished.emit(info)


class _InstallerDownloadWorker(QObject):
    finished = pyqtSignal(object, object)  # UpdateInfo, dest_path | None

    def __init__(self, info: UpdateInfo, dest: Path):
        super().__init__()
        self._info = info
        self._dest = dest

    def run(self) -> None:
        ok = updater.download_installer(self._info.installer_url, self._dest)
        self.finished.emit(self._info, self._dest if ok else None)


class _DowngradeFetchWorker(QObject):
    finished = pyqtSignal(object, object)  # UpdateInfo | None, dest_path | None

    def __init__(self, tag: str, dest_dir: Path):
        super().__init__()
        self._tag = tag
        self._dest_dir = dest_dir

    def run(self) -> None:
        info = updater.fetch_release(self._tag)
        if info is None or not info.installer_url:
            self.finished.emit(None, None)
            return
        dest = self._dest_dir / (
            info.installer_filename or f"TypeStream-Setup-{info.latest_version}.exe"
        )
        ok = updater.download_installer(info.installer_url, dest)
        self.finished.emit(info, dest if ok else None)


class AppController(QObject):
    _record_start = pyqtSignal()
    _record_stop = pyqtSignal()
    _record_toggle = pyqtSignal()
    _paste_last = pyqtSignal()
    _transcription_done = pyqtSignal(str, object)
    _transcription_failed = pyqtSignal(str)

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._config = Config.load()
        self._reconcile_installed_version()
        self._history = History(limit=self._config.history_limit)
        self._stats = Stats()
        self._recorder = AudioRecorder(input_device=self._config.input_device)
        self._transcriber = Transcriber(
            engine=self._config.engine,
            api_key=self._config.api_key,
            model=self._config.model,
            local_model_size=self._config.local_model_size,
            language=self._config.language,
            prompt=self._whisper_prompt(),
        )
        sounds.set_beep_volume(self._config.beep_volume)
        sounds.set_warning_volume(self._config.warning_volume)
        autostart.set_enabled(self._config.autostart)
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
        self._main_window = MainWindow(self._history, self._stats, self._config)
        self._main_window.settings_view().set_version_info(
            current=__version__,
            previous=self._config.previous_version,
            can_self_install=auto_install.can_self_install(),
        )
        self._overlay = RecordingOverlay()

        self._update_thread: QThread | None = None
        self._update_worker: _UpdateCheckWorker | None = None
        self._update_info: UpdateInfo | None = None
        # Path of a downloaded installer that's ready to run. None while no
        # update is queued, set once the background download finishes.
        self._update_installer_path: Path | None = None
        self._installer_dl_thread: QThread | None = None
        self._installer_dl_worker: _InstallerDownloadWorker | None = None
        self._downgrade_thread: QThread | None = None
        self._downgrade_worker: _DowngradeFetchWorker | None = None

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

        if self._config.engine == "openai" and not self._config.api_key:
            log.info("API key missing — settings dialog will auto-open")
            QTimer.singleShot(300, self.open_settings)
        elif self._config.engine == "local" and not local_engine.is_installed("whisper"):
            log.info(
                "Local engine selected but not installed — settings dialog will auto-open"
            )
            QTimer.singleShot(300, self.open_settings)
        else:
            log.info("Transcription engine ready (engine=%s)", self._config.engine)

        QTimer.singleShot(UPDATE_CHECK_DELAY_MS, self._start_update_check)

        threading.Thread(
            target=self._recorder.prewarm,
            name="recorder-prewarm",
            daemon=True,
        ).start()

    def _wire_signals(self) -> None:
        self._tray.open_history.connect(self.open_history)
        self._tray.open_settings.connect(self.open_settings)
        self._tray.copy_last.connect(self.copy_last)
        self._tray.quit_app.connect(self.quit)
        self._tray.style_changed.connect(self._on_style_changed)
        self._tray.update_clicked.connect(self._on_update_clicked)

        self._main_window.copy_requested.connect(self._on_copy_request)
        self._main_window.insert_requested.connect(self._on_insert_request)
        self._main_window.style_changed.connect(self._on_style_changed)
        self._main_window.install_update_clicked.connect(self._on_update_clicked)
        self._main_window.dismiss_update_clicked.connect(self._on_dismiss_update_clicked)
        self._main_window.settings_view().changed.connect(self._apply_settings_live)
        self._main_window.settings_view().style_changed.connect(self._on_style_changed)
        self._main_window.settings_view().rollback_requested.connect(self.request_downgrade)
        self._main_window.settings_view().check_updates_requested.connect(
            self._on_manual_update_check
        )

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
                log.info(
                    "Record hotkey registered as PTT (key=%s)",
                    self._config.record_hotkey,
                )
            else:
                self._hotkeys.register_record_toggle(
                    self._config.record_hotkey,
                    self._record_toggle.emit,
                )
                log.info(
                    "Record hotkey registered as TOGGLE (key=%s)",
                    self._config.record_hotkey,
                )
                if self._config.record_mode == "ptt":
                    self._notify(
                        "Tastenkombination erkannt — PTT wird als Toggle behandelt.",
                        "warn",
                    )
            self._hotkeys.register_paste(self._config.paste_hotkey, self._paste_last.emit)
        except Exception as e:
            log.exception("Hotkey registration failed")
            self._notify(f"Hotkey-Fehler: {e}", "error", important=True)

    def show_main_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def open_history(self) -> None:
        self._main_window.refresh()
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def open_settings(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()
        self._main_window.show_settings()

    def _apply_settings_live(self, new_cfg: Config) -> None:
        prev = self._config
        if new_cfg == prev:
            return
        self._config = new_cfg
        self._config.save()
        if new_cfg.history_limit != prev.history_limit:
            self._history.set_limit(new_cfg.history_limit)
        if new_cfg.input_device != prev.input_device:
            self._recorder.set_input_device(new_cfg.input_device)
            threading.Thread(
                target=self._recorder.prewarm,
                name="recorder-prewarm",
                daemon=True,
            ).start()
        if (
            new_cfg.engine != prev.engine
            or new_cfg.api_key != prev.api_key
            or new_cfg.model != prev.model
            or new_cfg.local_model_size != prev.local_model_size
            or new_cfg.language != prev.language
            or new_cfg.style != prev.style
            or new_cfg.style_mode != prev.style_mode
            or new_cfg.custom_style_prompt != prev.custom_style_prompt
        ):
            self._transcriber.update(
                engine=new_cfg.engine,
                api_key=new_cfg.api_key,
                model=new_cfg.model,
                local_model_size=new_cfg.local_model_size,
                language=new_cfg.language,
                prompt=self._whisper_prompt(),
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
        if new_cfg.beep_volume != prev.beep_volume:
            sounds.set_beep_volume(new_cfg.beep_volume)
        if new_cfg.warning_volume != prev.warning_volume:
            sounds.set_warning_volume(new_cfg.warning_volume)
        if new_cfg.autostart != prev.autostart:
            autostart.set_enabled(new_cfg.autostart)

    def _apply_theme(self) -> None:
        palette = get_palette(self._resolved_theme())
        self._app.setStyleSheet(build_qss(palette))
        self._overlay.apply_palette(palette)
        apply_card_shadow(self._main_window.history_widget(), palette)

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

    def _whisper_prompt(self) -> str:
        if self._config.style_mode == "refine":
            return ""
        return self._active_style_prompt()

    def _refresh_tray_styles(self) -> None:
        styles = all_styles(self._config.custom_style_prompt)
        if not any(s.key == self._config.style for s in styles):
            self._config.style = "original"
            self._config.save()
            self._transcriber.set_prompt(self._whisper_prompt())
        self._tray.update_styles(styles, self._config.style)
        self._main_window.update_styles(styles, self._config.style)
        self._main_window.settings_view().update_styles(styles, self._config.style)

    def _on_style_changed(self, key: str) -> None:
        if key == self._config.style:
            return
        self._config.style = key
        self._config.save()
        self._transcriber.set_prompt(self._whisper_prompt())
        self._tray.set_active_style(key)
        self._main_window.set_active_style(key)
        self._main_window.settings_view().set_active_style(key)
        label = find_style(key, self._config.custom_style_prompt).label
        self._notify(f"Stil: {label}", "info")

    def copy_last(self) -> None:
        latest = self._history.latest()
        if latest is None:
            self._notify("Kein Text im Verlauf.", "warn")
            return
        self._inserter.copy_to_clipboard(latest.text)
        self._notify("Letzter Text in Zwischenablage kopiert.", "info")

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
        if self._update_thread is not None:
            self._update_thread.quit()
            self._update_thread.wait(1500)
        self._tray.hide()
        self._app.quit()

    def _start_update_check(self, *, manual: bool = False) -> None:
        if self._update_thread is not None:
            if manual:
                # The Settings button is now disabled — reset it so the
                # user knows the request was acknowledged.
                self._main_window.settings_view().reset_check_updates_button(
                    found=self._update_info is not None
                )
            return
        log.info(
            "Starting %s update check (current=%s)",
            "manual" if manual else "background", __version__,
        )
        self._update_thread = QThread(self)
        self._update_worker = _UpdateCheckWorker()
        self._update_manual_pending = manual
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(
            self._on_update_check_finished, Qt.ConnectionType.QueuedConnection
        )
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_thread.finished.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.finished.connect(self._update_check_cleanup)
        self._update_thread.start()

    def _on_manual_update_check(self) -> None:
        self._start_update_check(manual=True)

    def _update_check_cleanup(self) -> None:
        self._update_thread = None
        self._update_worker = None

    def _on_update_check_finished(self, info) -> None:
        manual = getattr(self, "_update_manual_pending", False)
        self._update_manual_pending = False
        if not isinstance(info, UpdateInfo):
            info = None

        if manual:
            self._main_window.settings_view().reset_check_updates_button(
                found=info is not None
            )
            if info is None:
                self._notify("Du bist auf der aktuellsten Version.", "info")

        if info is None:
            return
        self._update_info = info
        log.info(
            "Update available: %s → %s (installer=%s)",
            info.current_version, info.latest_version,
            info.installer_url or "(no asset attached)",
        )

        if info.installer_url and auto_install.can_self_install():
            self._start_installer_download(info)
        else:
            # No .exe attached to the release (or running from source) —
            # fall back to the old behavior: tray menu opens the release
            # page in the browser. UI banner is *not* shown because there's
            # nothing to one-click-install.
            self._tray.set_update_available(info.latest_version)
            self._notify(
                f"Update verfügbar: v{info.latest_version} — siehe Tray-Menü.",
                "info",
            )

    def _start_installer_download(self, info: UpdateInfo) -> None:
        UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dest = UPDATE_CACHE_DIR / (
            info.installer_filename
            or f"TypeStream-Setup-{info.latest_version}.exe"
        )
        if dest.exists() and dest.stat().st_size > 0:
            log.info("Installer already cached at %s", dest)
            self._on_installer_ready(info, dest)
            return

        log.info("Starting installer download: %s", info.installer_url)
        thread = QThread(self)
        worker = _InstallerDownloadWorker(info, dest)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            self._on_installer_download_finished, Qt.ConnectionType.QueuedConnection
        )
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # Keep refs alive so QThread/QObject aren't GC'd mid-download.
        self._installer_dl_thread = thread
        self._installer_dl_worker = worker
        thread.start()

    def _on_installer_download_finished(self, info, dest) -> None:
        self._installer_dl_thread = None
        self._installer_dl_worker = None
        if not isinstance(info, UpdateInfo):
            return
        if dest is None:
            log.warning("Installer download failed — falling back to browser link")
            self._tray.set_update_available(info.latest_version)
            self._notify(
                f"Update v{info.latest_version} verfügbar — Download fehlgeschlagen, "
                "Release im Browser öffnen?",
                "warn",
            )
            return
        self._on_installer_ready(info, dest)

    def _on_installer_ready(self, info: UpdateInfo, installer: Path) -> None:
        self._update_info = info
        self._update_installer_path = installer
        self._tray.set_update_available(info.latest_version)
        self._main_window.show_update_banner(info.latest_version)
        self._main_window.settings_view().set_pending_update(
            info.latest_version, info.release_notes
        )
        self._notify(
            f"Update v{info.latest_version} ist bereit — im Hauptfenster auf "
            "'Jetzt installieren' klicken.",
            "info",
        )
        log.info("Installer ready at %s — UI install button enabled", installer)

    def _on_update_clicked(self) -> None:
        """Triggered by the tray menu and the main-window banner button.

        If the installer is downloaded and we can self-install, run it and
        quit. Otherwise (download still in progress, no asset attached, or
        running from source) fall back to opening the release page."""
        info = self._update_info
        if info is None:
            return
        if self._update_installer_path is not None and auto_install.can_self_install():
            self._run_installer(self._update_installer_path)
            return
        url = info.download_url
        log.info("No local installer — opening release page: %s", url)
        try:
            webbrowser.open(url, new=2)
        except Exception:
            log.exception("Failed to open update URL")
            self._notify(
                f"Konnte Browser nicht öffnen. URL: {url}",
                "error",
                important=True,
            )

    def _on_dismiss_update_clicked(self) -> None:
        """The banner X button — hide the banner for this session.

        The next launch will rediscover the same pending update and the
        banner will come back; that's intentional, so users don't quietly
        miss a critical fix."""
        self._main_window.hide_update_banner()
        log.info("Update banner dismissed by user for this session")

    def _run_installer(self, installer: Path) -> None:
        log.info("Launching installer %s and quitting app", installer)
        spawned = auto_install.launch_installer_and_quit(installer)
        if not spawned:
            self._notify(
                "Update-Installer konnte nicht gestartet werden — bitte manuell "
                f"ausführen: {installer}",
                "error",
                important=True,
            )
            return
        self.quit()

    def _reconcile_installed_version(self) -> None:
        """Detect that an install happened since the last launch and record
        what we just upgraded from, so Settings → Updates can offer a
        one-click rollback to that version."""
        seen = (self._config.installed_version_seen or "").strip()
        current = __version__
        if seen == current:
            return
        if seen and updater.is_newer(current, seen):
            # We just moved forward from `seen` to `current` — that's an
            # upgrade. Remember `seen` as the rollback target.
            log.info("Detected upgrade %s → %s", seen, current)
            self._config.previous_version = seen
        elif seen and updater.is_newer(seen, current):
            # We're now on an *older* version than we recorded — that's a
            # downgrade we just performed. Remember the version we left as
            # the new "previous", so the user can roll forward again.
            log.info("Detected downgrade %s → %s", seen, current)
            self._config.previous_version = seen
        # First-ever run with this field: don't invent a previous version.
        self._config.installed_version_seen = current
        self._config.save()

    def request_downgrade(self) -> None:
        """Called by Settings → Updates when the user clicks the rollback
        button. Downloads the previous-version installer in the background
        and runs it the same way as a forward update."""
        target = (self._config.previous_version or "").strip()
        if not target:
            self._notify("Keine vorherige Version bekannt.", "warn")
            return
        if not auto_install.can_self_install():
            self._notify(
                "Rollback geht nur aus der installierten App heraus — aus dem "
                "Dev-Checkout heraus nicht möglich.",
                "warn",
            )
            return
        if self._downgrade_thread is not None:
            self._notify("Rollback läuft bereits …", "info")
            return
        UPDATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._main_window.settings_view().set_downgrade_in_progress(target)
        thread = QThread(self)
        worker = _DowngradeFetchWorker(target, UPDATE_CACHE_DIR)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            self._on_downgrade_fetch_finished, Qt.ConnectionType.QueuedConnection
        )
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_downgrade_thread_finished)
        self._downgrade_thread = thread
        self._downgrade_worker = worker
        thread.start()

    def _on_downgrade_thread_finished(self) -> None:
        self._downgrade_thread = None
        self._downgrade_worker = None

    def _on_downgrade_fetch_finished(self, info, dest) -> None:
        self._main_window.settings_view().clear_downgrade_in_progress()
        if dest is None or not isinstance(dest, Path):
            target = self._config.previous_version
            self._notify(
                f"Rollback auf v{target} fehlgeschlagen — Release oder Installer "
                "nicht auf GitHub gefunden.",
                "error",
                important=True,
            )
            return
        log.info("Rollback installer ready at %s — launching", dest)
        self._run_installer(dest)

    def _update_tray_state(self) -> None:
        if self._state == STATE_RECORDING:
            self._tray.set_state_recording()
        elif self._pending_count > 0:
            self._tray.set_state_busy()
        else:
            self._tray.set_state_idle()

    def _notify(self, text: str, level: str = "warn", important: bool = False) -> None:
        """Show a notification through the overlay pill.

        When important=True, a warning chime additionally plays — reserved for
        cases where the user otherwise might miss that something needs their
        attention (failed paste, transcription error, setup blockers). Recording
        sounds (start/stop) take precedence; we skip the pill while recording so
        it doesn't cover the active overlay."""
        log.info("notify [%s%s] %s", level, " important" if important else "", text)
        if self._config.show_overlay and self._state != STATE_RECORDING:
            self._overlay.show_message(text, level)
        if important and self._config.play_sounds:
            sounds.play_warning()

    def _start_recording(self) -> None:
        if self._state != STATE_IDLE:
            return
        if self._config.engine == "openai" and not self._config.api_key:
            self._notify(
                "Kein API-Key gesetzt — bitte Einstellungen öffnen.",
                "error",
                important=True,
            )
            return
        if self._config.engine == "local" and not local_engine.is_installed("whisper"):
            self._notify(
                "Faster-Whisper ist nicht installiert — bitte Einstellungen öffnen.",
                "error",
                important=True,
            )
            return
        try:
            self._recorder.start()
        except Exception as e:
            self._notify(f"Aufnahme-Start fehlgeschlagen: {e}", "error", important=True)
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
            self._notify(f"Aufnahme-Stop fehlgeschlagen: {e}", "error", important=True)
            return
        if self._config.play_sounds:
            sounds.play_stop()
        self._state = STATE_IDLE
        if self._config.show_overlay:
            self._overlay.hide_with_fade()
        if wav is None:
            self._update_tray_state()
            self._notify(
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
                text, timings = self._run_transcription(wav)
                self._transcription_done.emit(text, timings)
            except Exception as e:
                log.exception("Transcription failed")
                self._transcription_failed.emit(str(e))
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except Exception:
                    pass

    def _active_engine_id(self) -> str:
        return "openai" if self._config.engine == "openai" else "whisper"

    def _run_transcription(self, wav: Path) -> tuple[str, dict]:
        cfg = self._config
        active = self._active_engine_id()
        log.info(
            "Transcription start: engine=%s active_id=%s benchmark=%s",
            cfg.engine, active, cfg.benchmark_mode,
        )
        if cfg.benchmark_mode:
            a, b = cfg.benchmark_engine_a, cfg.benchmark_engine_b
            if a != b and self._transcriber.can_run(a) and self._transcriber.can_run(b):
                text, timings = self._run_benchmark_pair(wav, a, b, active)
                return self._post_process(text), timings
            log.warning(
                "Benchmark requested but cannot run pair (%s, %s) — single-engine fallback.",
                a, b,
            )

        t0 = time.perf_counter()
        text = self._transcriber.transcribe_with(active, wav)
        elapsed = time.perf_counter() - t0
        timings: dict = {
            "engine_used": active,
            "timings": {active: elapsed},
        }
        if active == "openai":
            timings["cloud_seconds"] = elapsed
        elif active == "whisper":
            timings["local_seconds"] = elapsed
        log.info("Transcription done: engine=%s elapsed=%.2fs", active, elapsed)
        return self._post_process(text), timings

    def _post_process(self, text: str) -> str:
        if hallucinations.is_likely_silence(text, self._active_style_prompt()):
            log.info("Suppressed likely-silence output: %r", text[:80])
            return ""
        cfg = self._config
        style_prompt = self._active_style_prompt()
        if (
            cfg.style_mode == "refine"
            and style_prompt
            and cfg.api_key
            and text.strip()
        ):
            refined = refiner.refine_text(
                text,
                style_prompt,
                api_key=cfg.api_key,
                model=cfg.refine_model,
            )
            log.info("Refiner applied (style=%s, model=%s)", cfg.style, cfg.refine_model)
            return refined
        return text

    def _run_benchmark_pair(
        self, wav: Path, engine_a: str, engine_b: str, primary: str
    ) -> tuple[str, dict]:
        log.info(
            "Benchmark start: wav=%s pair=(%s, %s) primary=%s",
            wav.name, engine_a, engine_b, primary,
        )

        def run_leg(eid: str):
            log.info("Benchmark leg %s: dispatching…", eid)
            t0 = time.perf_counter()
            try:
                text = self._transcriber.transcribe_with(eid, wav)
                elapsed = time.perf_counter() - t0
                log.info("Benchmark leg %s ok: %.2fs (chars=%d)", eid, elapsed, len(text))
                return text, elapsed, None
            except Exception as e:
                log.exception("Benchmark leg %s failed", eid)
                return None, time.perf_counter() - t0, e

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="benchmark") as ex:
            f_a = ex.submit(run_leg, engine_a)
            f_b = ex.submit(run_leg, engine_b)
            text_a, secs_a, err_a = f_a.result()
            text_b, secs_b, err_b = f_b.result()

        log.info(
            "Benchmark done: %s=%.2fs%s %s=%.2fs%s",
            engine_a, secs_a, " (failed)" if err_a else "",
            engine_b, secs_b, " (failed)" if err_b else "",
        )

        legs: dict[str, tuple[str | None, float, Exception | None]] = {
            engine_a: (text_a, secs_a, err_a),
            engine_b: (text_b, secs_b, err_b),
        }

        timings_map: dict[str, float] = {}
        for eid, (_t, secs, err) in legs.items():
            if err is None:
                timings_map[eid] = secs

        primary_text, _, primary_err = legs.get(primary, (None, 0.0, None))
        if primary_text is None:
            # Fallback: nimm das andere Bein, falls die primäre Engine fehlschlug.
            for eid, (t, _s, err) in legs.items():
                if err is None and t is not None:
                    primary_text = t
                    log.warning("Primary leg %s failed — using %s instead.", primary, eid)
                    break
            if primary_text is None:
                raise primary_err or RuntimeError(
                    "Benchmark: keine Engine lieferte einen Text."
                )

        timings: dict = {
            "engine_used": primary,
            "timings": timings_map,
        }
        if "openai" in timings_map:
            timings["cloud_seconds"] = timings_map["openai"]
        if "whisper" in timings_map:
            timings["local_seconds"] = timings_map["whisper"]
        return primary_text, timings

    def _on_transcription_done(self, text: str, timings: object) -> None:
        with self._pending_lock:
            if self._pending_count > 0:
                self._pending_count -= 1
        self._update_tray_state()
        if not text:
            self._notify("Keine Sprache erkannt", "warn")
            return
        meta = timings if isinstance(timings, dict) else {}
        self._history.add(
            text,
            cloud_seconds=meta.get("cloud_seconds"),
            local_seconds=meta.get("local_seconds"),
            engine_used=meta.get("engine_used"),
            timings=meta.get("timings"),
        )
        self._stats.add_text(text)
        if self._main_window.isVisible():
            self._main_window.refresh()
        self._deliver_text(text)

    def _deliver_text(self, text: str) -> None:
        if not self._inserter.insert_at_cursor(text):
            self._notify(
                "Auto-Einfügen fehlgeschlagen — Text in Zwischenablage. Strg+V einfügen.",
                "warn",
                important=True,
            )

    def _on_transcription_failed(self, error: str) -> None:
        with self._pending_lock:
            if self._pending_count > 0:
                self._pending_count -= 1
        self._update_tray_state()
        self._notify(f"Transkription fehlgeschlagen: {error}", "error", important=True)

    def _paste_last_history(self) -> None:
        latest = self._history.latest()
        if latest is None:
            self._notify("Kein Text im Verlauf.", "warn")
            return
        QTimer.singleShot(80, lambda: self._deliver_text(latest.text))

    def _on_copy_request(self, text: str) -> None:
        self._inserter.copy_to_clipboard(text)
        self._notify("In Zwischenablage kopiert.", "info")

    def _on_insert_request(self, text: str) -> None:
        self._main_window.hide()
        QTimer.singleShot(120, lambda: self._deliver_text(text))
