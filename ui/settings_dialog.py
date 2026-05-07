from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from core.config import Config
from ui.hotkey_capture import HotkeyCaptureButton
from ui.style import style_mono_section, style_serif_title

MODELS = [
    ("gpt-4o-mini-transcribe", "gpt-4o-mini-transcribe  ·  ~$0.003/min"),
    ("whisper-1", "whisper-1  ·  ~$0.006/min"),
    ("gpt-4o-transcribe", "gpt-4o-transcribe  ·  ~$0.006/min  ·  beste Qualität"),
]

MODES = [
    ("ptt", "Push-to-Talk (Taste halten)"),
    ("toggle", "Toggle (Drücken: Start, nochmal: Stop)"),
]

THEMES = [
    ("system", "System (automatisch)"),
    ("dark", "Dunkel"),
    ("light", "Hell"),
]

LANGUAGES = [
    ("", "Auto-Erkennung"),
    ("de", "Deutsch"),
    ("en", "Englisch"),
    ("fr", "Französisch"),
    ("es", "Spanisch"),
    ("it", "Italienisch"),
    ("nl", "Niederländisch"),
    ("pt", "Portugiesisch"),
    ("pl", "Polnisch"),
    ("ja", "Japanisch"),
    ("zh", "Chinesisch"),
]


def _section(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setProperty("role", "section")
    style_mono_section(label)
    return label


class SettingsDialog(QDialog):
    changed = pyqtSignal(object)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._style = config.style
        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(580)

        title = QLabel("Einstellungen")
        title.setProperty("role", "title")
        style_serif_title(title, point_size=32)
        subtitle = QLabel("API, Hotkeys, Aufnahme und Erscheinungsbild")
        subtitle.setProperty("role", "muted")

        # --- API section ---
        self._api_key_edit = QLineEdit(config.api_key)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")

        self._model_combo = QComboBox()
        for value, label in MODELS:
            self._model_combo.addItem(label, value)
        idx = self._model_combo.findData(config.model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)

        self._language_combo = QComboBox()
        for value, label in LANGUAGES:
            self._language_combo.addItem(label, value)
        idx = self._language_combo.findData(config.language)
        if idx >= 0:
            self._language_combo.setCurrentIndex(idx)

        api_form = QFormLayout()
        api_form.setHorizontalSpacing(16)
        api_form.setVerticalSpacing(10)
        api_form.addRow("API-Key", self._api_key_edit)
        api_form.addRow("Modell", self._model_combo)
        api_form.addRow("Sprache", self._language_combo)

        # --- Hotkeys section ---
        self._record_hotkey_btn = HotkeyCaptureButton(config.record_hotkey)
        self._mode_combo = QComboBox()
        for value, label in MODES:
            self._mode_combo.addItem(label, value)
        idx = self._mode_combo.findData(config.record_mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        self._paste_hotkey_btn = HotkeyCaptureButton(config.paste_hotkey)

        hotkey_form = QFormLayout()
        hotkey_form.setHorizontalSpacing(16)
        hotkey_form.setVerticalSpacing(10)
        hotkey_form.addRow("Aufnahme", self._record_hotkey_btn)
        hotkey_form.addRow("Modus", self._mode_combo)
        hotkey_form.addRow("Letzten Text einfügen", self._paste_hotkey_btn)

        hotkey_hint = QLabel(
            "Klicke auf einen Button und drücke dann die gewünschte Taste oder Maustaste. "
            "Push-to-Talk benötigt eine einzelne Taste."
        )
        hotkey_hint.setWordWrap(True)
        hotkey_hint.setProperty("role", "muted")

        # --- Recording section ---
        self._min_duration_spin = QDoubleSpinBox()
        self._min_duration_spin.setRange(0.0, 3.0)
        self._min_duration_spin.setSingleStep(0.1)
        self._min_duration_spin.setDecimals(2)
        self._min_duration_spin.setSuffix(" s")
        self._min_duration_spin.setValue(config.min_record_duration)

        self._history_limit_spin = QSpinBox()
        self._history_limit_spin.setRange(5, 500)
        self._history_limit_spin.setValue(config.history_limit)

        self._play_sounds_check = QCheckBox("Akustisches Feedback (Start- / Stop-Ton)")
        self._play_sounds_check.setChecked(config.play_sounds)

        self._show_overlay_check = QCheckBox("Visuelles Overlay während Aufnahme")
        self._show_overlay_check.setChecked(config.show_overlay)

        rec_form = QFormLayout()
        rec_form.setHorizontalSpacing(16)
        rec_form.setVerticalSpacing(10)
        rec_form.addRow("Min. Aufnahme-Dauer", self._min_duration_spin)
        rec_form.addRow("Verlauf-Limit", self._history_limit_spin)
        rec_form.addRow("", self._play_sounds_check)
        rec_form.addRow("", self._show_overlay_check)

        # --- Appearance section ---
        self._theme_combo = QComboBox()
        for value, label in THEMES:
            self._theme_combo.addItem(label, value)
        idx = self._theme_combo.findData(config.theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

        appearance_form = QFormLayout()
        appearance_form.setHorizontalSpacing(16)
        appearance_form.setVerticalSpacing(10)
        appearance_form.addRow("Theme", self._theme_combo)

        # --- Style section ---
        self._custom_style_edit = QPlainTextEdit(config.custom_style_prompt)
        self._custom_style_edit.setPlaceholderText(
            "Optionaler eigener Stil-Prompt — z. B. ein Beispieltext im gewünschten "
            "Stil. Leer lassen, um nur die vordefinierten Stile zu nutzen."
        )
        self._custom_style_edit.setFixedHeight(96)

        style_form = QFormLayout()
        style_form.setHorizontalSpacing(16)
        style_form.setVerticalSpacing(10)
        style_form.addRow("Eigener Stil", self._custom_style_edit)

        style_hint = QLabel(
            "Den aktiven Stil wählst du im Tray-Menü unter „Stil“. "
            "Ein leerer Custom-Prompt blendet den Eintrag aus."
        )
        style_hint.setWordWrap(True)
        style_hint.setProperty("role", "muted")

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Speichern")
            ok_btn.setProperty("role", "primary")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # --- Compose ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 38, 44, 32)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        layout.addWidget(_section("OpenAI"))
        layout.addLayout(api_form)

        layout.addWidget(_section("Hotkeys"))
        layout.addLayout(hotkey_form)
        layout.addWidget(hotkey_hint)

        layout.addWidget(_section("Aufnahme"))
        layout.addLayout(rec_form)

        layout.addWidget(_section("Stil"))
        layout.addLayout(style_form)
        layout.addWidget(style_hint)

        layout.addWidget(_section("Erscheinungsbild"))
        layout.addLayout(appearance_form)

        layout.addSpacing(12)
        layout.addWidget(buttons)

        self._wire_change_signals()

    def _wire_change_signals(self) -> None:
        self._api_key_edit.textChanged.connect(self._emit_changed)
        self._model_combo.currentIndexChanged.connect(self._emit_changed)
        self._language_combo.currentIndexChanged.connect(self._emit_changed)
        self._mode_combo.currentIndexChanged.connect(self._emit_changed)
        self._record_hotkey_btn.captured.connect(self._emit_changed)
        self._paste_hotkey_btn.captured.connect(self._emit_changed)
        self._min_duration_spin.valueChanged.connect(self._emit_changed)
        self._history_limit_spin.valueChanged.connect(self._emit_changed)
        self._play_sounds_check.toggled.connect(self._emit_changed)
        self._show_overlay_check.toggled.connect(self._emit_changed)
        self._custom_style_edit.textChanged.connect(self._emit_changed)
        self._theme_combo.currentIndexChanged.connect(self._emit_changed)

    def _emit_changed(self, *_args) -> None:
        self.changed.emit(self.to_config())

    def to_config(self) -> Config:
        return Config(
            api_key=self._api_key_edit.text().strip(),
            model=self._model_combo.currentData(),
            language=self._language_combo.currentData(),
            record_hotkey=self._record_hotkey_btn.value() or "f9",
            paste_hotkey=self._paste_hotkey_btn.value() or "ctrl+alt+v",
            record_mode=self._mode_combo.currentData(),
            history_limit=self._history_limit_spin.value(),
            min_record_duration=float(self._min_duration_spin.value()),
            play_sounds=self._play_sounds_check.isChecked(),
            show_overlay=self._show_overlay_check.isChecked(),
            style=self._style,
            custom_style_prompt=self._custom_style_edit.toPlainText().strip(),
            theme=self._theme_combo.currentData() or "system",
        )
