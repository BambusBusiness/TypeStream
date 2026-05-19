from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from core import local_engine
from core.config import Config
from core.history import HistoryEntry
from core.i18n import SUPPORTED_LANGS, i18n
from core.recorder import list_input_devices
from core.styles import Style
from ui.hotkey_capture import HotkeyCaptureButton
from ui.local_engine_dialog import LocalEngineInstallDialog
from ui.style import style_mono_section, style_serif_title

# Each combo's options are stored as (config-value, translation-key)
# tuples. `_populate_combo` looks up the key via i18n at the moment it
# fills the combo, so a `language_changed` event can re-translate by
# re-populating with the same lists.

MODELS = [
    ("gpt-4o-mini-transcribe", "settings.transcription.model_mini"),
    ("whisper-1", "settings.transcription.model_whisper"),
    ("gpt-4o-transcribe", "settings.transcription.model_4o"),
]

ENGINES = [
    ("openai", "settings.transcription.engine_cloud"),
    ("local", "settings.transcription.engine_local"),
]

LOCAL_MODEL_SIZES = [
    ("tiny", "settings.transcription.local_tiny"),
    ("base", "settings.transcription.local_base"),
    ("small", "settings.transcription.local_small"),
]

MODES = [
    ("ptt", "settings.hotkeys.mode_ptt"),
    ("toggle", "settings.hotkeys.mode_toggle"),
]

STYLE_MODES = [
    ("hint", "settings.style.mode_hint"),
    ("refine", "settings.style.mode_refine"),
]

REFINE_MODELS = [
    ("gpt-4o-mini", "settings.style.refine_mini"),
    ("gpt-4o", "settings.style.refine_4o"),
]

BENCHMARK_ENGINES = [
    ("openai", "settings.stats.bench_openai"),
    ("whisper", "settings.stats.bench_whisper"),
]

THEMES = [
    ("system", "settings.display.theme_system"),
    ("dark", "settings.display.theme_dark"),
    ("light", "settings.display.theme_light"),
]

LANGUAGES = [
    ("",   "lang.auto"),
    ("de", "lang.de"),
    ("en", "lang.en"),
    ("fr", "lang.fr"),
    ("es", "lang.es"),
    ("it", "lang.it"),
    ("nl", "lang.nl"),
    ("pt", "lang.pt"),
    ("pl", "lang.pl"),
    ("ja", "lang.ja"),
    ("zh", "lang.zh"),
]

UI_LANGUAGES = [
    ("system", "settings.display.ui_language_system"),
    ("de",     "lang.de"),
    ("en",     "lang.en"),
]

NAV_KEYS = (
    "settings.nav.transcription",
    "settings.nav.hotkeys",
    "settings.nav.recording",
    "settings.nav.style",
    "settings.nav.display",
    "settings.nav.stats",
    "settings.nav.updates",
)


def _select(combo: QComboBox, value: object) -> None:
    idx = combo.findData(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _populate_combo(combo: QComboBox, options: list[tuple], current=None) -> None:
    """Fill `combo` with (value, translation-key) pairs from `options`,
    translating each key via i18n at call time. Preserves the current
    selection unless `current` is given, in which case that value is
    selected after re-populating."""
    target = current if current is not None else combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for value, key in options:
        combo.addItem(i18n.t(key), value)
    idx = combo.findData(target)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    combo.blockSignals(False)


def _muted_bind(key: str) -> QLabel:
    """QLabel pre-bound to a translation key so its text auto-updates on
    language change."""
    label = QLabel()
    label.setWordWrap(True)
    label.setProperty("role", "muted")
    i18n.bind(label.setText, key)
    return label


def _row_label_bind(key: str) -> QLabel:
    """A QLabel for QFormLayout.addRow(label, widget) bound to a key."""
    label = QLabel()
    i18n.bind(label.setText, key)
    return label


def _section_bind(key: str) -> QLabel:
    label = QLabel()
    style_mono_section(label)
    i18n.bind(label.setText, key)
    return label


class _HelpIcon(QToolButton):
    """Small `?` button that shows its tooltip on hover (standard Qt timing)
    and also on click — clicking forces the tooltip to appear immediately,
    in case the hover timing is too slow for the user. The tooltip text is
    held as a translation key so language switching just works."""

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self.setText("?")
        self.setProperty("role", "help")
        i18n.bind(self.setToolTip, key)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)
        self.clicked.connect(self._show_now)

    def _show_now(self) -> None:
        QToolTip.showText(QCursor.pos() + QPoint(8, 12), i18n.t(self._key), self)


def _help_icon(key: str) -> _HelpIcon:
    return _HelpIcon(key)


def _with_help(widget: QWidget, key: str) -> QWidget:
    """Wrap a widget plus a small `?`-tooltip icon in a single container so it
    can be used as the field side of QFormLayout.addRow()."""
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(widget, 1)
    row.addWidget(_help_icon(key), 0, Qt.AlignmentFlag.AlignVCenter)
    return container


def _page(content_layout: QVBoxLayout) -> QWidget:
    page = QWidget()
    page.setLayout(content_layout)
    return page


def _stats_card_widget(title_label: QLabel, value: QLabel, meta: QLabel) -> QFrame:
    card = QFrame()
    card.setObjectName("statsCard")
    inner = QVBoxLayout(card)
    inner.setContentsMargins(20, 18, 20, 18)
    inner.setSpacing(8)
    inner.addWidget(title_label)
    inner.addWidget(value)
    inner.addWidget(meta)
    return card


class SettingsView(QWidget):
    changed = pyqtSignal(object)
    back_requested = pyqtSignal()
    style_changed = pyqtSignal(str)
    rollback_requested = pyqtSignal()
    check_updates_requested = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._style_key = config.style
        self._emit_blocked = True
        # Combos whose option labels come from i18n. Re-populated on
        # language change (see _on_language_changed).
        self._translated_combos: list[tuple[QComboBox, list]] = []

        # ---- Transkription widgets ----
        self._engine_combo = QComboBox()
        self._translated_combos.append((self._engine_combo, ENGINES))
        _populate_combo(self._engine_combo, ENGINES, current=config.engine)

        self._api_key_edit = QLineEdit(config.api_key)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")

        self._model_combo = QComboBox()
        self._translated_combos.append((self._model_combo, MODELS))
        _populate_combo(self._model_combo, MODELS, current=config.model)

        self._local_size_combo = QComboBox()
        self._translated_combos.append((self._local_size_combo, LOCAL_MODEL_SIZES))
        _populate_combo(self._local_size_combo, LOCAL_MODEL_SIZES, current=config.local_model_size)

        self._language_combo = QComboBox()
        self._translated_combos.append((self._language_combo, LANGUAGES))
        _populate_combo(self._language_combo, LANGUAGES, current=config.language)

        self._api_key_label = _row_label_bind("settings.transcription.api_key")
        self._model_label = _row_label_bind("settings.transcription.model")
        self._local_size_label = _row_label_bind("settings.transcription.local_size")

        self._local_hint = _muted_bind("settings.transcription.local_hint")

        self._install_status = QLabel("")
        self._install_status.setWordWrap(True)
        self._install_btn = QPushButton()
        i18n.bind(self._install_btn.setText, "settings.transcription.install_btn")
        self._install_btn.setProperty("role", "primary")
        self._install_btn.clicked.connect(self._on_install_clicked)
        self._install_row_widgets = (self._install_status, self._install_btn)

        self._benchmark_check = QCheckBox()
        i18n.bind(self._benchmark_check.setText, "settings.transcription.benchmark")
        self._benchmark_check.setChecked(config.benchmark_mode)
        self._benchmark_hint = _muted_bind("settings.transcription.benchmark_hint")

        # ---- Hotkey widgets ----
        self._record_hotkey_btn = HotkeyCaptureButton(config.record_hotkey)
        self._mode_combo = QComboBox()
        self._translated_combos.append((self._mode_combo, MODES))
        _populate_combo(self._mode_combo, MODES, current=config.record_mode)
        self._paste_hotkey_btn = HotkeyCaptureButton(config.paste_hotkey)

        # ---- Aufnahme widgets ----
        self._input_device_combo = QComboBox()
        self._input_device_combo.setMinimumContentsLength(28)
        self._input_device_value = config.input_device
        self.refresh_input_devices()

        self._min_duration_spin = QDoubleSpinBox()
        self._min_duration_spin.setRange(0.0, 3.0)
        self._min_duration_spin.setSingleStep(0.1)
        self._min_duration_spin.setDecimals(2)
        self._min_duration_spin.setSuffix(" s")
        self._min_duration_spin.setValue(config.min_record_duration)

        self._history_limit_spin = QSpinBox()
        self._history_limit_spin.setRange(5, 500)
        self._history_limit_spin.setValue(config.history_limit)

        self._play_sounds_check = QCheckBox()
        i18n.bind(self._play_sounds_check.setText, "settings.recording.play_sounds")
        self._play_sounds_check.setChecked(config.play_sounds)

        self._beep_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._beep_volume_slider.setRange(0, 100)
        self._beep_volume_slider.setSingleStep(5)
        self._beep_volume_slider.setPageStep(10)
        self._beep_volume_slider.setMinimumHeight(28)
        self._beep_volume_slider.setValue(int(round(config.beep_volume * 100)))
        self._beep_volume_label = QLabel(f"{int(round(config.beep_volume * 100))} %")
        self._beep_volume_label.setProperty("role", "muted")
        self._beep_volume_label.setMinimumWidth(48)
        self._beep_volume_slider.valueChanged.connect(
            lambda v: self._beep_volume_label.setText(f"{v} %")
        )

        self._warning_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._warning_volume_slider.setRange(0, 100)
        self._warning_volume_slider.setSingleStep(5)
        self._warning_volume_slider.setPageStep(10)
        self._warning_volume_slider.setMinimumHeight(28)
        self._warning_volume_slider.setValue(int(round(config.warning_volume * 100)))
        self._warning_volume_label = QLabel(f"{int(round(config.warning_volume * 100))} %")
        self._warning_volume_label.setProperty("role", "muted")
        self._warning_volume_label.setMinimumWidth(48)
        self._warning_volume_slider.valueChanged.connect(
            lambda v: self._warning_volume_label.setText(f"{v} %")
        )

        self._show_overlay_check = QCheckBox()
        i18n.bind(self._show_overlay_check.setText, "settings.recording.show_overlay")
        self._show_overlay_check.setChecked(config.show_overlay)

        self._autostart_check = QCheckBox()
        i18n.bind(self._autostart_check.setText, "settings.recording.autostart")
        self._autostart_check.setChecked(config.autostart)

        # ---- Stil widgets ----
        self._active_style_combo = QComboBox()
        self._active_style_combo.setMinimumWidth(180)
        # Items are populated via update_styles() once the controller knows
        # the available styles (incl. optional custom prompt).

        self._style_mode_combo = QComboBox()
        self._translated_combos.append((self._style_mode_combo, STYLE_MODES))
        _populate_combo(self._style_mode_combo, STYLE_MODES, current=config.style_mode)

        self._refine_model_combo = QComboBox()
        self._translated_combos.append((self._refine_model_combo, REFINE_MODELS))
        _populate_combo(self._refine_model_combo, REFINE_MODELS, current=config.refine_model)
        self._refine_model_label = _row_label_bind("settings.style.refine_model")

        self._custom_style_edit = QPlainTextEdit(config.custom_style_prompt)
        i18n.bind(
            self._custom_style_edit.setPlaceholderText,
            "settings.style.custom_placeholder",
        )
        self._custom_style_edit.setFixedHeight(120)

        # ---- Anzeige widgets (formerly Erscheinungsbild) ----
        self._theme_combo = QComboBox()
        self._translated_combos.append((self._theme_combo, THEMES))
        _populate_combo(self._theme_combo, THEMES, current=config.theme)

        self._ui_language_combo = QComboBox()
        self._translated_combos.append((self._ui_language_combo, UI_LANGUAGES))
        _populate_combo(self._ui_language_combo, UI_LANGUAGES, current=config.ui_language)

        # ---- Statistik widgets ----
        self._benchmark_a_combo = QComboBox()
        self._benchmark_b_combo = QComboBox()
        self._translated_combos.append((self._benchmark_a_combo, BENCHMARK_ENGINES))
        self._translated_combos.append((self._benchmark_b_combo, BENCHMARK_ENGINES))
        _populate_combo(self._benchmark_a_combo, BENCHMARK_ENGINES, current=config.benchmark_engine_a)
        _populate_combo(self._benchmark_b_combo, BENCHMARK_ENGINES, current=config.benchmark_engine_b)

        self._stats_a_title = QLabel("")
        self._stats_a_title.setProperty("role", "section")
        style_mono_section(self._stats_a_title)
        self._stats_a_value = QLabel("—")
        self._stats_a_value.setProperty("role", "stats-value")
        self._stats_a_meta = QLabel("")
        self._stats_a_meta.setProperty("role", "muted")

        self._stats_b_title = QLabel("")
        self._stats_b_title.setProperty("role", "section")
        style_mono_section(self._stats_b_title)
        self._stats_b_value = QLabel("—")
        self._stats_b_value.setProperty("role", "stats-value")
        self._stats_b_meta = QLabel("")
        self._stats_b_meta.setProperty("role", "muted")

        self._stats_verdict = QLabel("")
        self._stats_verdict.setProperty("role", "muted")
        self._stats_verdict.setWordWrap(True)
        # Cache the engine labels we're displaying so language switches can
        # re-resolve them via i18n without losing which engines are picked.
        self._stats_last_entries: list = []

        # ---- Updates widgets ----
        # The controller fills these in via set_version_info() once it has
        # decided whether self-install is even possible (dev checkout vs.
        # PyInstaller bundle) and which previous version, if any, the user
        # can roll back to.
        self._current_version_label = QLabel("")
        style_mono_section(self._current_version_label)
        self._pending_update_label = QLabel("")
        self._pending_update_label.setWordWrap(True)
        self._pending_update_label.setProperty("role", "muted")
        self._previous_version_label = QLabel("")
        self._previous_version_label.setWordWrap(True)
        self._previous_version_label.setProperty("role", "muted")
        self._rollback_btn = QPushButton("Auf vorherige Version zurück")
        self._rollback_btn.setProperty("role", "danger")
        self._rollback_btn.setEnabled(False)
        self._rollback_btn.clicked.connect(self.rollback_requested.emit)
        # set_version_info() overwrites this — the default keeps the page
        # in a sensible state if it's opened before the controller wires up.
        self._can_self_install = False

        self._check_updates_btn = QPushButton()
        i18n.bind(self._check_updates_btn.setText, "settings.updates.check_btn_idle")
        self._check_updates_btn.clicked.connect(self._on_check_updates_clicked)

        # Tracked values for re-rendering on language change.
        self._last_previous_version = ""
        self._pending_update_version = ""
        self._pending_update_notes = ""
        self._stats_last_entries = []

        # Persistent status pane at the bottom of the Updates page: any
        # notify(error|warn) coming out of the auto-update or rollback
        # flow lands here so the user can read it later instead of
        # chasing the brief overlay pill. Empty = hidden, so the page
        # stays clean on the happy path.
        self._update_status_label = QLabel("")
        self._update_status_label.setWordWrap(True)
        self._update_status_label.setProperty("role", "update-status")
        self._update_status_label.setVisible(False)

        # ---- Build pages ----
        pages = [
            self._build_transcription_page(),
            self._build_hotkeys_page(),
            self._build_recording_page(),
            self._build_style_page(),
            self._build_appearance_page(),
            self._build_stats_page(),
            self._build_updates_page(),
        ]

        # ---- Sidebar ----
        # Tuned so all NAV_ITEMS fit without a vertical scrollbar at the
        # default window height (620). Adding more nav entries should
        # either bump the window minimum height or shrink padding further.
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebarNav")
        self._sidebar.setFixedWidth(174)
        self._sidebar.setSpacing(1)
        self._sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        for key in NAV_KEYS:
            self._sidebar.addItem(QListWidgetItem(i18n.t(key)))
        self._sidebar.setCurrentRow(0)

        # ---- Stack ----
        self._stack = QStackedWidget()
        for w in pages:
            self._stack.addWidget(w)
        self._stack.setCurrentIndex(0)
        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._update_style_mode_visibility()

        # ---- Header ----
        self._back_btn = QPushButton()
        i18n.bind(self._back_btn.setText, "settings.back")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested.emit)

        title = QLabel()
        title.setProperty("role", "title")
        style_serif_title(title, point_size=30)
        i18n.bind(title.setText, "settings.title")

        header = QHBoxLayout()
        header.setSpacing(16)
        header.addWidget(self._back_btn)
        header.addStretch()

        title_row = QHBoxLayout()
        title_row.setSpacing(0)
        title_row.addWidget(title)
        title_row.addStretch()

        body = QHBoxLayout()
        body.setSpacing(28)
        body.addWidget(self._sidebar)
        body.addWidget(self._stack, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 28)
        layout.setSpacing(18)
        layout.addLayout(header)
        layout.addLayout(title_row)
        layout.addSpacing(4)
        layout.addLayout(body, 1)

        self._update_engine_visibility()
        self._wire_change_signals()
        i18n.language_changed.connect(self._on_language_changed)
        self._emit_blocked = False

    def _on_language_changed(self) -> None:
        """Re-translate combo option labels and any dynamic strings that
        don't go through i18n.bind (sidebar items, dynamic stats labels,
        etc.). i18n.bind already handled the static labels."""
        was_blocked = self._emit_blocked
        self._emit_blocked = True
        try:
            for combo, options in self._translated_combos:
                _populate_combo(combo, options)
            for i, key in enumerate(NAV_KEYS):
                item = self._sidebar.item(i)
                if item is not None:
                    item.setText(i18n.t(key))
            # Static styles list — labels come from styles.py and are not
            # currently translated, so just re-trigger the dropdown.
            if hasattr(self, "_active_style_combo"):
                # styles labels are passed in via update_styles(), leave
                # them as-is (the controller may re-call update_styles
                # later).
                pass
            self.update_stats(self._stats_last_entries)
            # Rollback button text uses dynamic version interpolation —
            # ask the helper to re-apply with the same data.
            self._refresh_rollback_state(self._last_previous_version)
            self._refresh_pending_update()
        finally:
            self._emit_blocked = was_blocked

    # ----- public API -----

    def reset_to_first_page(self) -> None:
        self._sidebar.setCurrentRow(0)
        self._stack.setCurrentIndex(0)

    def update_styles(self, styles: list[Style], active_key: str) -> None:
        self._active_style_combo.blockSignals(True)
        self._active_style_combo.clear()
        for s in styles:
            self._active_style_combo.addItem(s.label, s.key)
        idx = self._active_style_combo.findData(active_key)
        if idx >= 0:
            self._active_style_combo.setCurrentIndex(idx)
        self._style_key = active_key
        self._active_style_combo.blockSignals(False)

    def set_active_style(self, key: str) -> None:
        self._style_key = key
        idx = self._active_style_combo.findData(key)
        if idx < 0 or idx == self._active_style_combo.currentIndex():
            return
        self._active_style_combo.blockSignals(True)
        self._active_style_combo.setCurrentIndex(idx)
        self._active_style_combo.blockSignals(False)

    def _on_active_style_changed(self, _index: int) -> None:
        key = self._active_style_combo.currentData()
        if not key or key == self._style_key:
            return
        self._style_key = key
        if not self._emit_blocked:
            self.style_changed.emit(key)

    def refresh_input_devices(self) -> None:
        """Re-enumerate audio devices and preserve current selection if still
        present. Called on init and from MainWindow.show_settings() so plugged-
        /unplugged microphones surface without an app restart."""
        was_blocked = self._emit_blocked
        self._emit_blocked = True
        try:
            current = self._input_device_value
            self._input_device_combo.blockSignals(True)
            self._input_device_combo.clear()
            self._input_device_combo.addItem(i18n.t("settings.recording.system_default"), "")
            for name, label in list_input_devices():
                self._input_device_combo.addItem(label, name)
            idx = self._input_device_combo.findData(current)
            if idx >= 0:
                self._input_device_combo.setCurrentIndex(idx)
            else:
                # Saved device disappeared — show it as inactive so the user
                # sees what was selected, even though it will fall back to
                # the system default on the next recording.
                if current:
                    self._input_device_combo.addItem(
                        current + i18n.t("settings.recording.unavailable_suffix"),
                        current,
                    )
                    self._input_device_combo.setCurrentIndex(
                        self._input_device_combo.count() - 1
                    )
                else:
                    self._input_device_combo.setCurrentIndex(0)
            self._input_device_combo.blockSignals(False)
        finally:
            self._emit_blocked = was_blocked

    def _on_input_device_changed(self, _index: int) -> None:
        self._input_device_value = self._input_device_combo.currentData() or ""
        self._emit_changed()

    def update_stats(self, entries: Iterable[HistoryEntry]) -> None:
        last10 = list(entries)[:10]
        self._stats_last_entries = last10
        a_id = self._benchmark_a_combo.currentData() or "openai"
        b_id = self._benchmark_b_combo.currentData() or "whisper"
        bench_key = {"openai": "settings.stats.bench_openai",
                     "whisper": "settings.stats.bench_whisper"}
        a_label = i18n.t(bench_key.get(a_id, "")) if a_id in bench_key else a_id
        b_label = i18n.t(bench_key.get(b_id, "")) if b_id in bench_key else b_id

        a_times: list[float] = []
        b_times: list[float] = []
        for e in last10:
            t = e.all_timings()
            if a_id in t:
                a_times.append(t[a_id])
            if b_id in t:
                b_times.append(t[b_id])

        self._stats_a_title.setText(a_label.upper())
        self._stats_b_title.setText(b_label.upper())

        if a_times:
            avg = sum(a_times) / len(a_times)
            self._stats_a_value.setText(i18n.t("settings.stats.avg", seconds=avg))
            self._stats_a_meta.setText(i18n.t("settings.stats.count", count=len(a_times)))
        else:
            self._stats_a_value.setText("—")
            self._stats_a_meta.setText(i18n.t("settings.stats.no_data"))

        if b_times:
            avg = sum(b_times) / len(b_times)
            self._stats_b_value.setText(i18n.t("settings.stats.avg", seconds=avg))
            self._stats_b_meta.setText(i18n.t("settings.stats.count", count=len(b_times)))
        else:
            self._stats_b_value.setText("—")
            self._stats_b_meta.setText(i18n.t("settings.stats.no_data"))

        if a_times and b_times and a_id != b_id:
            aavg = sum(a_times) / len(a_times)
            bavg = sum(b_times) / len(b_times)
            if aavg < bavg:
                ratio = bavg / aavg if aavg > 0 else 0
                self._stats_verdict.setText(
                    i18n.t("settings.stats.verdict_faster_a",
                           a=a_label, b=b_label, ratio=ratio)
                )
            elif bavg < aavg:
                ratio = aavg / bavg if bavg > 0 else 0
                self._stats_verdict.setText(
                    i18n.t("settings.stats.verdict_faster_b",
                           a=a_label, b=b_label, ratio=ratio)
                )
            else:
                self._stats_verdict.setText(i18n.t("settings.stats.verdict_equal"))
        elif a_id == b_id:
            self._stats_verdict.setText(i18n.t("settings.stats.verdict_same_pair"))
        else:
            self._stats_verdict.setText(i18n.t("settings.stats.verdict_benchmark_off"))

    def set_config(self, config: Config) -> None:
        self._emit_blocked = True
        try:
            self._style_key = config.style
            _select(self._engine_combo, config.engine)
            if self._api_key_edit.text() != config.api_key:
                self._api_key_edit.setText(config.api_key)
            _select(self._model_combo, config.model)
            _select(self._local_size_combo, config.local_model_size)
            _select(self._language_combo, config.language)
            self._record_hotkey_btn.setValue(config.record_hotkey)
            _select(self._mode_combo, config.record_mode)
            self._paste_hotkey_btn.setValue(config.paste_hotkey)
            self._min_duration_spin.setValue(config.min_record_duration)
            self._history_limit_spin.setValue(config.history_limit)
            if config.input_device != self._input_device_value:
                self._input_device_value = config.input_device
                self.refresh_input_devices()
            self._play_sounds_check.setChecked(config.play_sounds)
            self._beep_volume_slider.setValue(int(round(config.beep_volume * 100)))
            self._warning_volume_slider.setValue(int(round(config.warning_volume * 100)))
            self._show_overlay_check.setChecked(config.show_overlay)
            self._autostart_check.setChecked(config.autostart)
            _select(self._style_mode_combo, config.style_mode)
            _select(self._refine_model_combo, config.refine_model)
            if self._custom_style_edit.toPlainText() != config.custom_style_prompt:
                self._custom_style_edit.setPlainText(config.custom_style_prompt)
            _select(self._theme_combo, config.theme)
            _select(self._ui_language_combo, config.ui_language)
            self._benchmark_check.setChecked(config.benchmark_mode)
            _select(self._benchmark_a_combo, config.benchmark_engine_a)
            _select(self._benchmark_b_combo, config.benchmark_engine_b)
            self._update_engine_visibility()
            self._update_style_mode_visibility()
        finally:
            self._emit_blocked = False

    def to_config(self) -> Config:
        return Config(
            engine=self._engine_combo.currentData() or "openai",
            api_key=self._api_key_edit.text().strip(),
            model=self._model_combo.currentData(),
            local_model_size=self._local_size_combo.currentData() or "base",
            language=self._language_combo.currentData(),
            record_hotkey=self._record_hotkey_btn.value() or "f9",
            paste_hotkey=self._paste_hotkey_btn.value() or "ctrl+alt+v",
            record_mode=self._mode_combo.currentData(),
            history_limit=self._history_limit_spin.value(),
            min_record_duration=float(self._min_duration_spin.value()),
            input_device=self._input_device_value,
            play_sounds=self._play_sounds_check.isChecked(),
            beep_volume=self._beep_volume_slider.value() / 100.0,
            warning_volume=self._warning_volume_slider.value() / 100.0,
            show_overlay=self._show_overlay_check.isChecked(),
            autostart=self._autostart_check.isChecked(),
            style=self._style_key,
            style_mode=self._style_mode_combo.currentData() or "hint",
            refine_model=self._refine_model_combo.currentData() or "gpt-4o-mini",
            custom_style_prompt=self._custom_style_edit.toPlainText().strip(),
            theme=self._theme_combo.currentData() or "system",
            ui_language=self._ui_language_combo.currentData() or "system",
            benchmark_mode=self._benchmark_check.isChecked(),
            benchmark_engine_a=self._benchmark_a_combo.currentData() or "openai",
            benchmark_engine_b=self._benchmark_b_combo.currentData() or "whisper",
        )

    # ----- page builders -----

    def _build_transcription_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(
            _row_label_bind("settings.transcription.engine"),
            _with_help(self._engine_combo, "settings.transcription.engine_help"),
        )
        form.addRow(
            self._api_key_label,
            _with_help(self._api_key_edit, "settings.transcription.api_key_help"),
        )
        form.addRow(
            self._model_label,
            _with_help(self._model_combo, "settings.transcription.model_help"),
        )
        form.addRow(
            self._local_size_label,
            _with_help(self._local_size_combo, "settings.transcription.local_size_help"),
        )
        form.addRow(
            _row_label_bind("settings.transcription.language"),
            _with_help(self._language_combo, "settings.transcription.language_help"),
        )

        install_row = QHBoxLayout()
        install_row.setSpacing(12)
        install_row.addWidget(self._install_status, 1)
        install_row.addWidget(self._install_btn)

        benchmark_row = QHBoxLayout()
        benchmark_row.setSpacing(8)
        benchmark_row.addWidget(self._benchmark_check)
        benchmark_row.addWidget(_help_icon("settings.transcription.benchmark_help"))
        benchmark_row.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addLayout(install_row)
        layout.addWidget(self._local_hint)
        layout.addSpacing(8)
        layout.addLayout(benchmark_row)
        layout.addWidget(self._benchmark_hint)
        layout.addStretch()
        return _page(layout)

    def _build_stats_page(self) -> QWidget:
        intro = _muted_bind("settings.stats.intro")

        pair_form = QFormLayout()
        pair_form.setHorizontalSpacing(16)
        pair_form.setVerticalSpacing(8)
        pair_form.addRow(
            _row_label_bind("settings.stats.engine_a"),
            _with_help(self._benchmark_a_combo, "settings.stats.engine_a_help"),
        )
        pair_form.addRow(
            _row_label_bind("settings.stats.engine_b"),
            _with_help(self._benchmark_b_combo, "settings.stats.engine_b_help"),
        )

        a_card = _stats_card_widget(self._stats_a_title, self._stats_a_value, self._stats_a_meta)
        b_card = _stats_card_widget(self._stats_b_title, self._stats_b_value, self._stats_b_meta)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(a_card, 1)
        cards.addWidget(b_card, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(pair_form)
        layout.addWidget(intro)
        layout.addLayout(cards)
        layout.addWidget(self._stats_verdict)
        layout.addStretch()
        return _page(layout)

    def _build_hotkeys_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(
            _row_label_bind("settings.hotkeys.record"),
            _with_help(self._record_hotkey_btn, "settings.hotkeys.record_help"),
        )
        form.addRow(
            _row_label_bind("settings.hotkeys.mode"),
            _with_help(self._mode_combo, "settings.hotkeys.mode_help"),
        )
        form.addRow(
            _row_label_bind("settings.hotkeys.paste"),
            _with_help(self._paste_hotkey_btn, "settings.hotkeys.paste_help"),
        )

        hint = _muted_bind("settings.hotkeys.hint")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addStretch()
        return _page(layout)

    def _build_recording_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(_row_label_bind("settings.recording.microphone"), self._input_device_combo)
        form.addRow(_row_label_bind("settings.recording.min_duration"), self._min_duration_spin)
        form.addRow(_row_label_bind("settings.recording.history_limit"), self._history_limit_spin)
        form.addRow("", self._play_sounds_check)

        volume_row = QHBoxLayout()
        volume_row.setSpacing(12)
        volume_row.addWidget(self._beep_volume_slider, 1)
        volume_row.addWidget(self._beep_volume_label)
        volume_container = QWidget()
        volume_container.setLayout(volume_row)
        form.addRow(_row_label_bind("settings.recording.beep_volume"), volume_container)

        warning_row = QHBoxLayout()
        warning_row.setSpacing(12)
        warning_row.addWidget(self._warning_volume_slider, 1)
        warning_row.addWidget(self._warning_volume_label)
        warning_container = QWidget()
        warning_container.setLayout(warning_row)
        form.addRow(_row_label_bind("settings.recording.warning_volume"), warning_container)

        form.addRow("", self._show_overlay_check)
        form.addRow("", self._autostart_check)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addStretch()
        return _page(layout)

    def _build_style_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(
            _row_label_bind("settings.style.active"),
            _with_help(self._active_style_combo, "settings.style.active_help"),
        )
        form.addRow(
            _row_label_bind("settings.style.mode"),
            _with_help(self._style_mode_combo, "settings.style.mode_help"),
        )
        form.addRow(
            self._refine_model_label,
            _with_help(self._refine_model_combo, "settings.style.refine_model_help"),
        )
        form.addRow(
            _row_label_bind("settings.style.custom"),
            _with_help(self._custom_style_edit, "settings.style.custom_help"),
        )

        hint = _muted_bind("settings.style.hint_body")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addStretch()
        return _page(layout)

    def _update_style_mode_visibility(self) -> None:
        is_refine = self._style_mode_combo.currentData() == "refine"
        self._refine_model_label.setVisible(is_refine)
        self._refine_model_combo.setVisible(is_refine)

    def _build_updates_page(self) -> QWidget:
        current_section = _section_bind("settings.updates.current_section")
        pending_section = _section_bind("settings.updates.pending_section")
        rollback_section = _section_bind("settings.updates.rollback_section")
        intro = _muted_bind("settings.updates.intro")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(intro)
        layout.addSpacing(8)
        layout.addWidget(current_section)
        layout.addWidget(self._current_version_label)
        layout.addWidget(self._check_updates_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(12)
        layout.addWidget(pending_section)
        layout.addWidget(self._pending_update_label)
        layout.addSpacing(12)
        layout.addWidget(rollback_section)
        layout.addWidget(self._previous_version_label)
        layout.addWidget(self._rollback_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        layout.addWidget(self._update_status_label)
        return _page(layout)

    def set_update_status(self, text: str, level: str = "error") -> None:
        if not text:
            self._update_status_label.clear()
            self._update_status_label.setVisible(False)
            return
        self._update_status_label.setProperty("role", f"update-status-{level}")
        self._update_status_label.setText(text)
        self._update_status_label.setVisible(True)
        # Re-polish so the role-based selector picks up the new value.
        self._update_status_label.style().unpolish(self._update_status_label)
        self._update_status_label.style().polish(self._update_status_label)

    def clear_update_status(self) -> None:
        self.set_update_status("")

    def _on_check_updates_clicked(self) -> None:
        self._check_updates_btn.setEnabled(False)
        self._check_updates_btn.setText(i18n.t("settings.updates.check_btn_running"))
        self.check_updates_requested.emit()

    def reset_check_updates_button(self, *, found: bool) -> None:
        # `found=True` means a new release is available — the banner/UI
        # banner takes over from here, so the button just goes back to
        # idle. `found=False` flashes a short "Aktuell" confirmation so
        # the user gets a visible result when nothing happens.
        self._check_updates_btn.setEnabled(True)
        if found:
            self._check_updates_btn.setText(i18n.t("settings.updates.check_btn_idle"))
        else:
            self._check_updates_btn.setText(i18n.t("settings.updates.check_btn_up_to_date"))

    # ----- public API for the controller -----

    def set_version_info(
        self, *, current: str, previous: str, can_self_install: bool
    ) -> None:
        self._current_version_label.setText(f"v{current}")
        self._can_self_install = can_self_install
        self._last_previous_version = previous
        self._refresh_rollback_state(previous)
        self._refresh_pending_update()

    def _refresh_pending_update(self) -> None:
        # Only emit the placeholder text if we haven't already set a real
        # "downloaded and ready" message (the controller calls
        # set_pending_update() once the download finishes).
        if not getattr(self, "_pending_update_version", ""):
            self._pending_update_label.setText(i18n.t("settings.updates.no_update"))
            return
        version = self._pending_update_version
        notes = getattr(self, "_pending_update_notes", "")
        snippet = (notes or "").strip().splitlines()
        first_line = snippet[0].strip() if snippet else ""
        body = i18n.t("settings.updates.pending_ready", version=version)
        if first_line:
            body += "\n" + i18n.t("settings.updates.pending_notes", notes=first_line)
        self._pending_update_label.setText(body)

    def _refresh_rollback_state(self, previous: str) -> None:
        previous = (previous or "").strip()
        if not previous:
            self._previous_version_label.setText(
                i18n.t("settings.updates.rollback_no_history")
            )
            self._rollback_btn.setEnabled(False)
            self._rollback_btn.setText(i18n.t("settings.updates.rollback_btn_default"))
            return
        if not getattr(self, "_can_self_install", False):
            self._previous_version_label.setText(
                i18n.t("settings.updates.rollback_only_installed", version=previous)
            )
            self._rollback_btn.setEnabled(False)
            self._rollback_btn.setText(
                i18n.t("settings.updates.rollback_btn_target", version=previous)
            )
            return
        self._previous_version_label.setText(
            i18n.t("settings.updates.rollback_description", version=previous)
        )
        self._rollback_btn.setEnabled(True)
        self._rollback_btn.setText(
            i18n.t("settings.updates.rollback_btn_target", version=previous)
        )

    def set_pending_update(self, version: str, notes: str) -> None:
        self._pending_update_version = version
        self._pending_update_notes = notes
        self._refresh_pending_update()

    def set_downgrade_in_progress(self, target: str) -> None:
        self._rollback_btn.setEnabled(False)
        self._rollback_btn.setText(
            i18n.t("settings.updates.rollback_btn_loading", version=target)
        )

    def clear_downgrade_in_progress(self) -> None:
        # The successful path tears the app down right after this; this
        # call only matters on the failure path, where we re-enable the
        # button so the user can retry.
        self._rollback_btn.setEnabled(True)
        self._rollback_btn.setText(i18n.t("settings.updates.rollback_btn_default"))

    def _build_appearance_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow(
            _row_label_bind("settings.display.theme"),
            _with_help(self._theme_combo, "settings.display.theme_help"),
        )
        form.addRow(
            _row_label_bind("settings.display.ui_language"),
            _with_help(self._ui_language_combo, "settings.display.ui_language_help"),
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addStretch()
        return _page(layout)

    # ----- behavior -----

    def _update_engine_visibility(self) -> None:
        engine = self._engine_combo.currentData()
        is_openai = engine == "openai"
        self._api_key_label.setVisible(is_openai)
        self._api_key_edit.setVisible(is_openai)
        self._model_label.setVisible(is_openai)
        self._model_combo.setVisible(is_openai)
        self._local_size_label.setVisible(not is_openai)
        self._local_size_combo.setVisible(not is_openai)
        self._local_hint.setVisible(not is_openai)
        self._refresh_install_state()

    def _refresh_install_state(self) -> None:
        is_local = self._engine_combo.currentData() == "local"
        installed = local_engine.is_installed("whisper") if is_local else True
        for w in self._install_row_widgets:
            w.setVisible(is_local and not installed)
        if is_local and not installed:
            self._install_status.setText(i18n.t("settings.transcription.install_missing"))
            self._install_btn.setText(i18n.t("settings.transcription.install_btn_whisper"))

    def _on_install_clicked(self) -> None:
        dialog = LocalEngineInstallDialog(kind="whisper", parent=self)
        dialog.exec()
        if dialog.was_successful():
            self._refresh_install_state()
            if not self._emit_blocked:
                self.changed.emit(self.to_config())

    def _wire_change_signals(self) -> None:
        self._engine_combo.currentIndexChanged.connect(self._update_engine_visibility)
        self._engine_combo.currentIndexChanged.connect(self._emit_changed)
        self._api_key_edit.textChanged.connect(self._emit_changed)
        self._model_combo.currentIndexChanged.connect(self._emit_changed)
        self._local_size_combo.currentIndexChanged.connect(self._emit_changed)
        self._language_combo.currentIndexChanged.connect(self._emit_changed)
        self._mode_combo.currentIndexChanged.connect(self._emit_changed)
        self._record_hotkey_btn.captured.connect(self._emit_changed)
        self._paste_hotkey_btn.captured.connect(self._emit_changed)
        self._input_device_combo.currentIndexChanged.connect(self._on_input_device_changed)
        self._min_duration_spin.valueChanged.connect(self._emit_changed)
        self._history_limit_spin.valueChanged.connect(self._emit_changed)
        self._play_sounds_check.toggled.connect(self._emit_changed)
        self._beep_volume_slider.valueChanged.connect(self._emit_changed)
        self._warning_volume_slider.valueChanged.connect(self._emit_changed)
        self._show_overlay_check.toggled.connect(self._emit_changed)
        self._autostart_check.toggled.connect(self._emit_changed)
        self._active_style_combo.currentIndexChanged.connect(self._on_active_style_changed)
        self._style_mode_combo.currentIndexChanged.connect(self._update_style_mode_visibility)
        self._style_mode_combo.currentIndexChanged.connect(self._emit_changed)
        self._refine_model_combo.currentIndexChanged.connect(self._emit_changed)
        self._custom_style_edit.textChanged.connect(self._emit_changed)
        self._theme_combo.currentIndexChanged.connect(self._emit_changed)
        self._ui_language_combo.currentIndexChanged.connect(self._emit_changed)
        self._benchmark_check.toggled.connect(self._emit_changed)
        self._benchmark_a_combo.currentIndexChanged.connect(self._emit_changed)
        self._benchmark_b_combo.currentIndexChanged.connect(self._emit_changed)

    def _emit_changed(self, *_args) -> None:
        if self._emit_blocked:
            return
        self.changed.emit(self.to_config())
