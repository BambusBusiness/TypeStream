from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.history import History, HistoryEntry
from core.stats import Stats
from core.styles import Style
from ui.style import style_mono_section, style_serif_title


class MainWindow(QMainWindow):
    insert_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    settings_requested = pyqtSignal()
    style_changed = pyqtSignal(str)

    def __init__(self, history: History, stats: Stats):
        super().__init__()
        self._history = history
        self._stats = stats
        self.setWindowTitle("TypeStream")
        self.resize(720, 580)

        central = QWidget()
        central.setObjectName("appCentral")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 36, 40, 32)
        layout.setSpacing(24)

        # Header row: title + subtitle (left), settings button (right)
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
        header.addWidget(self._settings_btn)
        layout.addLayout(header)

        # History list
        self._list = QListWidget()
        self._list.setWordWrap(True)
        self._list.setSpacing(0)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list, 1)

        # Empty state label (shown when list is empty)
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

        self.setCentralWidget(central)

        self._copy_btn.clicked.connect(self._on_copy)
        self._insert_btn.clicked.connect(self._on_insert)
        self._delete_btn.clicked.connect(self._on_delete)
        self._clear_btn.clicked.connect(self._on_clear)
        self._settings_btn.clicked.connect(self.settings_requested.emit)

        self.refresh()

    def list_widget(self) -> QListWidget:
        return self._list

    def refresh(self) -> None:
        self._stats_label.setText(
            f"{self._stats.today:,} Wörter heute  ·  {self._stats.total:,} Wörter gesamt".replace(",", ".")
        )
        self._list.clear()
        entries = self._history.all()
        for e in entries:
            text = e.text if len(e.text) <= 220 else e.text[:220] + "…"
            item = QListWidgetItem(f"{text}\n{e.timestamp}")
            self._list.addItem(item)
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
