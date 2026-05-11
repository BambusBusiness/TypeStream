from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from core.history import History, HistoryEntry
from core.stats import Stats
from core.styles import Style
from ui.settings_view import SettingsView
from ui.style import style_mono_section, style_serif_title

PAGE_HISTORY = 0
PAGE_SETTINGS = 1


def _format_timestamp(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return ts


_ENGINE_LABELS = {
    "openai": "OpenAI",
    "whisper": "Whisper",
}


def _benchmark_text(entry: HistoryEntry) -> str:
    timings = entry.all_timings()
    if len(timings) < 2:
        return ""
    parts = [
        f"{_ENGINE_LABELS.get(k, k)} {v:.2f}s"
        for k, v in timings.items()
    ]
    fastest = min(timings, key=lambda k: timings[k])
    parts.append(f"{_ENGINE_LABELS.get(fastest, fastest)} schneller")
    return "  ·  ".join(parts)


class HistoryRow(QWidget):
    def __init__(self, entry: HistoryEntry, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        text = entry.text if len(entry.text) <= 220 else entry.text[:220] + "…"
        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setProperty("role", "history-text")
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self._text_label.setIndent(0)
        self._text_label.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_label)

        meta = QHBoxLayout()
        meta.setSpacing(0)
        meta.setContentsMargins(0, 0, 0, 0)
        self._timestamp_label = QLabel(_format_timestamp(entry.timestamp))
        self._timestamp_label.setProperty("role", "timestamp")
        meta.addWidget(self._timestamp_label)

        bench_text = _benchmark_text(entry)
        if bench_text:
            self._bench_label = QLabel(bench_text)
            self._bench_label.setProperty("role", "benchmark")
            meta.addWidget(self._bench_label)

        meta.addStretch()
        layout.addLayout(meta)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)


class HistoryListWidget(QListWidget):
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.recalc_item_sizes()

    def recalc_item_sizes(self) -> None:
        viewport_width = self.viewport().width() - 28
        if viewport_width <= 0:
            return
        for i in range(self.count()):
            item = self.item(i)
            w = self.itemWidget(item)
            if w is None:
                continue
            w.setFixedWidth(viewport_width)
            layout = w.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            w.adjustSize()
            item.setSizeHint(QSize(viewport_width, w.sizeHint().height()))


class MainWindow(QMainWindow):
    insert_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    style_changed = pyqtSignal(str)

    def __init__(self, history: History, stats: Stats, config: Config):
        super().__init__()
        self._history = history
        self._stats = stats
        self.setWindowTitle("TypeStream")
        self.resize(820, 620)

        central = QWidget()
        central.setObjectName("appCentral")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._history_page = self._build_history_page()
        self._stack.addWidget(self._history_page)  # PAGE_HISTORY

        self._settings_view = SettingsView(config)
        self._settings_view.back_requested.connect(self.show_history)
        self._stack.addWidget(self._settings_view)  # PAGE_SETTINGS

        self._stack.setCurrentIndex(PAGE_HISTORY)
        self.setCentralWidget(central)
        self.refresh()

    # ----- view navigation -----

    def show_history(self) -> None:
        self._stack.setCurrentIndex(PAGE_HISTORY)
        self.refresh()

    def show_settings(self) -> None:
        self._settings_view.update_stats(self._history.all())
        self._settings_view.reset_to_first_page()
        self._stack.setCurrentIndex(PAGE_SETTINGS)

    def settings_view(self) -> SettingsView:
        return self._settings_view

    # ----- history page -----

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 36, 40, 32)
        layout.setSpacing(24)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        title = QLabel("TypeStream")
        title.setProperty("role", "title")
        style_serif_title(title, point_size=30)
        self._stats_label = QLabel("")
        self._stats_label.setProperty("role", "muted")
        title_col.addWidget(title)
        title_col.addWidget(self._stats_label)
        header.addLayout(title_col)
        header.addStretch()

        style_label = QLabel("STIL")
        style_label.setProperty("role", "section")
        style_mono_section(style_label)
        header.addWidget(style_label)
        self._style_combo = QComboBox()
        self._style_combo.setMinimumWidth(180)
        self._style_combo.currentIndexChanged.connect(self._on_style_combo_changed)
        header.addWidget(self._style_combo)

        self._settings_btn = QPushButton("Einstellungen")
        self._settings_btn.clicked.connect(self.show_settings)
        header.addWidget(self._settings_btn)
        layout.addLayout(header)

        # History list
        self._list = HistoryListWidget()
        self._list.setSpacing(0)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list, 1)

        # Empty state
        self._empty_label = QLabel(
            "Noch keine Transkriptionen.\n"
            "Halte deinen Aufnahme-Hotkey, sprich kurz, lass los — der Text erscheint hier."
        )
        self._empty_label.setProperty("role", "muted")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("padding: 40px;")
        layout.addWidget(self._empty_label, 1)

        # Action row
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self._copy_btn = QPushButton("Kopieren")
        self._copy_btn.setProperty("role", "primary")
        self._insert_btn = QPushButton("Einfügen")
        self._delete_btn = QPushButton("Löschen")
        self._delete_btn.setProperty("role", "danger")
        actions.addWidget(self._copy_btn)
        actions.addWidget(self._insert_btn)
        actions.addStretch()
        actions.addWidget(self._delete_btn)
        self._clear_btn = QPushButton("Alle löschen")
        self._clear_btn.setProperty("role", "danger")
        actions.addWidget(self._clear_btn)
        layout.addLayout(actions)

        self._copy_btn.clicked.connect(self._on_copy)
        self._insert_btn.clicked.connect(self._on_insert)
        self._delete_btn.clicked.connect(self._on_delete)
        self._clear_btn.clicked.connect(self._on_clear)

        return page

    def list_widget(self) -> QListWidget:
        return self._list

    def refresh(self) -> None:
        self._stats_label.setText(
            f"{self._stats.today:,} Wörter heute  ·  {self._stats.total:,} Wörter gesamt".replace(",", ".")
        )
        self._list.clear()
        entries = self._history.all()
        for entry in entries:
            item = QListWidgetItem()
            self._list.addItem(item)
            row = HistoryRow(entry)
            self._list.setItemWidget(item, row)
        self._list.recalc_item_sizes()

        if entries:
            self._list.setCurrentRow(0)
            self._list.show()
            self._empty_label.hide()
            self._copy_btn.setEnabled(True)
            self._insert_btn.setEnabled(True)
            self._delete_btn.setEnabled(True)
            self._clear_btn.setEnabled(True)
        else:
            self._list.hide()
            self._empty_label.show()
            self._copy_btn.setEnabled(False)
            self._insert_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._clear_btn.setEnabled(False)

        # Keep statistics page live whenever history changes
        self._settings_view.update_stats(entries)

    def _selected_entry(self) -> HistoryEntry | None:
        row = self._list.currentRow()
        entries = self._history.all()
        if 0 <= row < len(entries):
            return entries[row]
        return None

    def _on_copy(self) -> None:
        e = self._selected_entry()
        if e is not None:
            self.copy_requested.emit(e.text)

    def _on_insert(self) -> None:
        e = self._selected_entry()
        if e is not None:
            self.insert_requested.emit(e.text)

    def _on_double_click(self, _item: QListWidgetItem) -> None:
        self._on_copy()

    def _on_delete(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._history.remove(row)
            self.refresh()

    def _on_clear(self) -> None:
        self._history.clear()
        self.refresh()

    def update_styles(self, styles: list[Style], active_key: str) -> None:
        self._style_combo.blockSignals(True)
        self._style_combo.clear()
        for s in styles:
            self._style_combo.addItem(s.label, s.key)
        idx = self._style_combo.findData(active_key)
        if idx >= 0:
            self._style_combo.setCurrentIndex(idx)
        self._style_combo.blockSignals(False)

    def set_active_style(self, key: str) -> None:
        idx = self._style_combo.findData(key)
        if idx < 0 or idx == self._style_combo.currentIndex():
            return
        self._style_combo.blockSignals(True)
        self._style_combo.setCurrentIndex(idx)
        self._style_combo.blockSignals(False)

    def _on_style_combo_changed(self, _index: int) -> None:
        key = self._style_combo.currentData()
        if key:
            self.style_changed.emit(key)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()
