from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
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
    QVBoxLayout,
    QWidget,
)

from core import local_engine
from core.config import Config
from core.history import HistoryEntry
from ui.hotkey_capture import HotkeyCaptureButton
from ui.local_engine_dialog import LocalEngineInstallDialog
from ui.style import style_mono_section, style_serif_title

MODELS = [
    ("gpt-4o-mini-transcribe", "gpt-4o-mini-transcribe  ·  ~$0.003/min"),
    ("whisper-1", "whisper-1  ·  ~$0.006/min"),
    ("gpt-4o-transcribe", "gpt-4o-transcribe  ·  ~$0.006/min  ·  beste Qualität"),
]

ENGINES = [
    ("openai", "OpenAI API (Cloud)"),
    ("local", "Faster-Whisper (Lokal)"),
]

LOCAL_MODEL_SIZES = [
    ("tiny", "tiny  ·  ~75 MB  ·  schnellste"),
    ("base", "base  ·  ~150 MB  ·  empfohlen"),
    ("small", "small  ·  ~470 MB  ·  beste Qualität"),
]

MODES = [
    ("ptt", "Push-to-Talk (Taste halten)"),
    ("toggle", "Toggle (Drücken: Start, nochmal: Stop)"),
]

STYLE_MODES = [
    ("hint", "Whisper-Hint  ·  schnell, kostenlos"),
    ("refine", "LLM-Refine  ·  extra GPT-Aufruf, teurer"),
]

REFINE_MODELS = [
    ("gpt-4o-mini", "gpt-4o-mini  ·  günstig, schnell"),
    ("gpt-4o", "gpt-4o  ·  beste Qualität"),
]

BENCHMARK_ENGINES = [
    ("openai", "OpenAI (Cloud)"),
    ("whisper", "Faster-Whisper (Lokal)"),
]

BENCHMARK_ENGINE_LABELS = {k: v for k, v in BENCHMARK_ENGINES}

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

NAV_ITEMS = (
    "Transkription",
    "Hotkeys",
    "Aufnahme",
    "Stil",
    "Erscheinungsbild",
    "Statistik",
)


def _select(combo: QComboBox, value: object) -> None:
    idx = combo.findData(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("role", "muted")
    return label


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

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._style_key = config.style
        self._emit_blocked = True

        # ---- Transkription widgets ----
        self._engine_combo = QComboBox()
        for v, l in ENGINES:
            self._engine_combo.addItem(l, v)
        _select(self._engine_combo, config.engine)

        self._api_key_edit = QLineEdit(config.api_key)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")

        self._model_combo = QComboBox()
        for v, l in MODELS:
            self._model_combo.addItem(l, v)
        _select(self._model_combo, config.model)

        self._local_size_combo = QComboBox()
        for v, l in LOCAL_MODEL_SIZES:
            self._local_size_combo.addItem(l, v)
        _select(self._local_size_combo, config.local_model_size)

        self._language_combo = QComboBox()
        for v, l in LANGUAGES:
            self._language_combo.addItem(l, v)
        _select(self._language_combo, config.language)

        self._api_key_label = QLabel("API-Key")
        self._model_label = QLabel("Modell")
        self._local_size_label = QLabel("Modell-Größe")

        self._local_hint = _muted(
            "Lokale Modelle werden in dein Benutzerverzeichnis geladen "
            "(AppData/Local/TypeStream/models). Keine Daten verlassen deinen Rechner."
        )

        self._install_status = QLabel("")
        self._install_status.setWordWrap(True)
        self._install_btn = QPushButton("Lokale Engine installieren")
        self._install_btn.setProperty("role", "primary")
        self._install_btn.clicked.connect(self._on_install_clicked)
        self._install_row_widgets = (self._install_status, self._install_btn)

        self._benchmark_check = QCheckBox(
            "Benchmark-Modus (beide Engines vergleichen)"
        )
        self._benchmark_check.setChecked(config.benchmark_mode)
        self._benchmark_hint = _muted(
            "Jede Aufnahme wird gleichzeitig durch OpenAI und Faster-Whisper geschickt. "
            "Beide Laufzeiten landen unter „Statistik“. Die Einfügung kommt aus der "
            "oben gewählten Quelle."
        )

        # ---- Hotkey widgets ----
        self._record_hotkey_btn = HotkeyCaptureButton(config.record_hotkey)
        self._mode_combo = QComboBox()
        for v, l in MODES:
            self._mode_combo.addItem(l, v)
        _select(self._mode_combo, config.record_mode)
        self._paste_hotkey_btn = HotkeyCaptureButton(config.paste_hotkey)

        # ---- Aufnahme widgets ----
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

        self._show_overlay_check = QCheckBox("Visuelles Overlay während Aufnahme")
        self._show_overlay_check.setChecked(config.show_overlay)

        self._autostart_check = QCheckBox("Bei Windows-Start automatisch starten")
        self._autostart_check.setChecked(config.autostart)

        # ---- Stil widgets ----
        self._style_mode_combo = QComboBox()
        for v, l in STYLE_MODES:
            self._style_mode_combo.addItem(l, v)
        _select(self._style_mode_combo, config.style_mode)

        self._refine_model_combo = QComboBox()
        for v, l in REFINE_MODELS:
            self._refine_model_combo.addItem(l, v)
        _select(self._refine_model_combo, config.refine_model)
        self._refine_model_label = QLabel("Refine-Modell")

        self._custom_style_edit = QPlainTextEdit(config.custom_style_prompt)
        self._custom_style_edit.setPlaceholderText(
            "Optionaler eigener Stil-Prompt — z. B. ein Beispieltext im gewünschten "
            "Stil. Leer lassen, um nur die vordefinierten Stile zu nutzen."
        )
        self._custom_style_edit.setFixedHeight(120)

        # ---- Erscheinungsbild widgets ----
        self._theme_combo = QComboBox()
        for v, l in THEMES:
            self._theme_combo.addItem(l, v)
        _select(self._theme_combo, config.theme)

        # ---- Statistik widgets ----
        self._benchmark_a_combo = QComboBox()
        self._benchmark_b_combo = QComboBox()
        for v, l in BENCHMARK_ENGINES:
            self._benchmark_a_combo.addItem(l, v)
            self._benchmark_b_combo.addItem(l, v)
        _select(self._benchmark_a_combo, config.benchmark_engine_a)
        _select(self._benchmark_b_combo, config.benchmark_engine_b)

        self._stats_a_title = QLabel(
            BENCHMARK_ENGINE_LABELS.get(config.benchmark_engine_a, config.benchmark_engine_a).upper()
        )
        self._stats_a_title.setProperty("role", "section")
        style_mono_section(self._stats_a_title)
        self._stats_a_value = QLabel("—")
        self._stats_a_value.setProperty("role", "stats-value")
        self._stats_a_meta = QLabel("noch keine Daten")
        self._stats_a_meta.setProperty("role", "muted")

        self._stats_b_title = QLabel(
            BENCHMARK_ENGINE_LABELS.get(config.benchmark_engine_b, config.benchmark_engine_b).upper()
        )
        self._stats_b_title.setProperty("role", "section")
        style_mono_section(self._stats_b_title)
        self._stats_b_value = QLabel("—")
        self._stats_b_value.setProperty("role", "stats-value")
        self._stats_b_meta = QLabel("noch keine Daten")
        self._stats_b_meta.setProperty("role", "muted")

        self._stats_verdict = QLabel(
            "Aktiviere den Benchmark-Modus, um beide Engines zu vergleichen."
        )
        self._stats_verdict.setProperty("role", "muted")
        self._stats_verdict.setWordWrap(True)

        # ---- Build pages ----
        pages = [
            self._build_transcription_page(),
            self._build_hotkeys_page(),
            self._build_recording_page(),
            self._build_style_page(),
            self._build_appearance_page(),
            self._build_stats_page(),
        ]

        # ---- Sidebar ----
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebarNav")
        self._sidebar.setFixedWidth(200)
        self._sidebar.setSpacing(2)
        self._sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        for label in NAV_ITEMS:
            self._sidebar.addItem(QListWidgetItem(label))
        self._sidebar.setCurrentRow(0)

        # ---- Stack ----
        self._stack = QStackedWidget()
        for w in pages:
            self._stack.addWidget(w)
        self._stack.setCurrentIndex(0)
        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._update_style_mode_visibility()

        # ---- Header ----
        self._back_btn = QPushButton("← Verlauf")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested.emit)

        title = QLabel("Einstellungen")
        title.setProperty("role", "title")
        style_serif_title(title, point_size=30)

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
        self._emit_blocked = False

    # ----- public API -----

    def reset_to_first_page(self) -> None:
        self._sidebar.setCurrentRow(0)
        self._stack.setCurrentIndex(0)

    def update_stats(self, entries: Iterable[HistoryEntry]) -> None:
        last10 = list(entries)[:10]
        a_id = self._benchmark_a_combo.currentData() or "openai"
        b_id = self._benchmark_b_combo.currentData() or "whisper"
        a_label = BENCHMARK_ENGINE_LABELS.get(a_id, a_id)
        b_label = BENCHMARK_ENGINE_LABELS.get(b_id, b_id)

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
            self._stats_a_value.setText(f"Ø {avg:.2f} s")
            self._stats_a_meta.setText(f"n = {len(a_times)}")
        else:
            self._stats_a_value.setText("—")
            self._stats_a_meta.setText("noch keine Daten")

        if b_times:
            avg = sum(b_times) / len(b_times)
            self._stats_b_value.setText(f"Ø {avg:.2f} s")
            self._stats_b_meta.setText(f"n = {len(b_times)}")
        else:
            self._stats_b_value.setText("—")
            self._stats_b_meta.setText("noch keine Daten")

        if a_times and b_times and a_id != b_id:
            aavg = sum(a_times) / len(a_times)
            bavg = sum(b_times) / len(b_times)
            if aavg < bavg:
                ratio = bavg / aavg if aavg > 0 else 0
                self._stats_verdict.setText(
                    f"{a_label} ist im Mittel {ratio:.1f}× schneller als {b_label}."
                )
            elif bavg < aavg:
                ratio = aavg / bavg if bavg > 0 else 0
                self._stats_verdict.setText(
                    f"{b_label} ist im Mittel {ratio:.1f}× schneller als {a_label}."
                )
            else:
                self._stats_verdict.setText("Beide Engines sind gleich schnell.")
        elif a_id == b_id:
            self._stats_verdict.setText(
                "Wähle zwei verschiedene Engines, um sie zu vergleichen."
            )
        else:
            self._stats_verdict.setText(
                "Aktiviere den Benchmark-Modus, um beide Engines zu vergleichen."
            )

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
            benchmark_mode=self._benchmark_check.isChecked(),
            benchmark_engine_a=self._benchmark_a_combo.currentData() or "openai",
            benchmark_engine_b=self._benchmark_b_combo.currentData() or "whisper",
        )

    # ----- page builders -----

    def _build_transcription_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow("Quelle", self._engine_combo)
        form.addRow(self._api_key_label, self._api_key_edit)
        form.addRow(self._model_label, self._model_combo)
        form.addRow(self._local_size_label, self._local_size_combo)
        form.addRow("Sprache", self._language_combo)

        install_row = QHBoxLayout()
        install_row.setSpacing(12)
        install_row.addWidget(self._install_status, 1)
        install_row.addWidget(self._install_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addLayout(install_row)
        layout.addWidget(self._local_hint)
        layout.addSpacing(8)
        layout.addWidget(self._benchmark_check)
        layout.addWidget(self._benchmark_hint)
        layout.addStretch()
        return _page(layout)

    def _build_stats_page(self) -> QWidget:
        intro = _muted(
            "Durchschnittliche Transkriptions-Latenz der letzten 10 Aufnahmen "
            "für das gewählte Engine-Paar."
        )

        pair_form = QFormLayout()
        pair_form.setHorizontalSpacing(16)
        pair_form.setVerticalSpacing(8)
        pair_form.addRow("Engine A", self._benchmark_a_combo)
        pair_form.addRow("Engine B", self._benchmark_b_combo)

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
        form.addRow("Aufnahme", self._record_hotkey_btn)
        form.addRow("Modus", self._mode_combo)
        form.addRow("Letzten Text einfügen", self._paste_hotkey_btn)

        hint = _muted(
            "Klicke auf einen Button und drücke dann die gewünschte Taste oder "
            "Maustaste. Push-to-Talk benötigt eine einzelne Taste."
        )

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
        form.addRow("Min. Aufnahme-Dauer", self._min_duration_spin)
        form.addRow("Verlauf-Limit", self._history_limit_spin)
        form.addRow("", self._play_sounds_check)

        volume_row = QHBoxLayout()
        volume_row.setSpacing(12)
        volume_row.addWidget(self._beep_volume_slider, 1)
        volume_row.addWidget(self._beep_volume_label)
        volume_container = QWidget()
        volume_container.setLayout(volume_row)
        form.addRow("Aufnahme-Ton", volume_container)

        warning_row = QHBoxLayout()
        warning_row.setSpacing(12)
        warning_row.addWidget(self._warning_volume_slider, 1)
        warning_row.addWidget(self._warning_volume_label)
        warning_container = QWidget()
        warning_container.setLayout(warning_row)
        form.addRow("Warnton", warning_container)

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
        form.addRow("Stil-Modus", self._style_mode_combo)
        form.addRow(self._refine_model_label, self._refine_model_combo)
        form.addRow("Eigener Stil", self._custom_style_edit)

        hint = _muted(
            "Whisper-Hint: günstig, der Stil-Beispieltext wird als Prompt an Whisper "
            "geschickt — der Effekt ist subtil.\n"
            "LLM-Refine: das fertige Transkript wird zusätzlich an GPT geschickt und "
            "konsequent umformuliert — kostet einen weiteren API-Aufruf pro Aufnahme.\n\n"
            "Den aktiven Stil wählst du im Tray-Menü oder oben im Hauptfenster unter „Stil“. "
            "Ein leerer Custom-Prompt blendet den Eintrag aus."
        )

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

    def _build_appearance_page(self) -> QWidget:
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow("Theme", self._theme_combo)

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
            self._install_status.setText(
                "Faster-Whisper ist auf diesem Rechner noch nicht installiert."
            )
            self._install_btn.setText("Faster-Whisper installieren")

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
        self._min_duration_spin.valueChanged.connect(self._emit_changed)
        self._history_limit_spin.valueChanged.connect(self._emit_changed)
        self._play_sounds_check.toggled.connect(self._emit_changed)
        self._beep_volume_slider.valueChanged.connect(self._emit_changed)
        self._warning_volume_slider.valueChanged.connect(self._emit_changed)
        self._show_overlay_check.toggled.connect(self._emit_changed)
        self._autostart_check.toggled.connect(self._emit_changed)
        self._style_mode_combo.currentIndexChanged.connect(self._update_style_mode_visibility)
        self._style_mode_combo.currentIndexChanged.connect(self._emit_changed)
        self._refine_model_combo.currentIndexChanged.connect(self._emit_changed)
        self._custom_style_edit.textChanged.connect(self._emit_changed)
        self._theme_combo.currentIndexChanged.connect(self._emit_changed)
        self._benchmark_check.toggled.connect(self._emit_changed)
        self._benchmark_a_combo.currentIndexChanged.connect(self._emit_changed)
        self._benchmark_b_combo.currentIndexChanged.connect(self._emit_changed)

    def _emit_changed(self, *_args) -> None:
        if self._emit_blocked:
            return
        self.changed.emit(self.to_config())
