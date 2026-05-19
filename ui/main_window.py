from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from core.history import History, HistoryEntry
from core.i18n import i18n
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


class HistoryRow(QFrame):
    clicked = pyqtSignal(int)
    double_clicked = pyqtSignal(int)

    def __init__(self, index: int, entry: HistoryEntry, parent=None):
        super().__init__(parent)
        self._index = index
        self.setObjectName("historyRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(7)

        text_label = QLabel(entry.text)
        text_label.setWordWrap(True)
        text_label.setProperty("role", "history-text")
        text_label.setIndent(0)
        text_label.setContentsMargins(0, 0, 0, 0)
        text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(text_label)

        meta = QHBoxLayout()
        meta.setSpacing(12)
        meta.setContentsMargins(0, 0, 0, 0)
        timestamp_label = QLabel(_format_timestamp(entry.timestamp))
        timestamp_label.setProperty("role", "timestamp")
        timestamp_label.setIndent(0)
        timestamp_label.setContentsMargins(0, 0, 0, 0)
        timestamp_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        meta.addWidget(timestamp_label)

        bench_text = _benchmark_text(entry)
        if bench_text:
            bench_label = QLabel(bench_text)
            bench_label.setProperty("role", "benchmark")
            bench_label.setIndent(0)
            bench_label.setContentsMargins(0, 0, 0, 0)
            meta.addWidget(bench_label)

        layout.addLayout(meta)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        # Dynamic-property selectors (`[selected="true"]`) only repaint after
        # an unpolish/polish cycle, otherwise the border stays stale.
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._index)
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    insert_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    style_changed = pyqtSignal(str)
    install_update_clicked = pyqtSignal()
    dismiss_update_clicked = pyqtSignal()

    def __init__(self, history: History, stats: Stats, config: Config):
        super().__init__()
        self._history = history
        self._stats = stats
        self._rows: list[HistoryRow] = []
        self._selected_index: int = -1
        self._pending_banner_version: str = ""
        i18n.bind(self.setWindowTitle, "app.title")
        self.resize(820, 620)
        i18n.language_changed.connect(self._on_language_changed)

        central = QWidget()
        central.setObjectName("appCentral")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._update_banner = self._build_update_banner()
        outer.addWidget(self._update_banner)
        self._update_banner.hide()

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

    def _build_update_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("updateBanner")
        banner.setProperty("role", "update-banner")
        banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        row = QHBoxLayout(banner)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(14)

        self._update_banner_label = QLabel("")
        self._update_banner_label.setProperty("role", "update-banner-text")
        row.addWidget(self._update_banner_label, 1)

        self._install_btn = QPushButton()
        self._install_btn.setProperty("role", "primary")
        self._install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._install_btn.clicked.connect(self.install_update_clicked.emit)
        i18n.bind(self._install_btn.setText, "banner.install_now")
        row.addWidget(self._install_btn, 0)

        dismiss = QPushButton("✕")
        dismiss.setProperty("role", "icon")
        i18n.bind(dismiss.setToolTip, "banner.dismiss_tooltip")
        dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss.setFixedSize(28, 28)
        dismiss.clicked.connect(self.dismiss_update_clicked.emit)
        row.addWidget(dismiss, 0)

        return banner

    def show_update_banner(self, version: str) -> None:
        self._pending_banner_version = version
        self._update_banner_label.setText(
            i18n.t("banner.update_ready", version=version)
        )
        self._update_banner.show()

    def hide_update_banner(self) -> None:
        self._pending_banner_version = ""
        self._update_banner.hide()

    def _on_language_changed(self) -> None:
        # Re-render dynamic (format-string-containing) labels that aren't
        # plain i18n.bind() candidates.
        if self._pending_banner_version:
            self._update_banner_label.setText(
                i18n.t("banner.update_ready", version=self._pending_banner_version)
            )
        self.refresh()

    # ----- view navigation -----

    def show_history(self) -> None:
        self._stack.setCurrentIndex(PAGE_HISTORY)
        self.refresh()

    def show_settings(self) -> None:
        self._settings_view.update_stats(self._history.all())
        self._settings_view.refresh_input_devices()
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
        title = QLabel()
        title.setProperty("role", "title")
        style_serif_title(title, point_size=30)
        i18n.bind(title.setText, "app.title")
        self._stats_label = QLabel("")
        self._stats_label.setProperty("role", "muted")
        title_col.addWidget(title)
        title_col.addWidget(self._stats_label)
        header.addLayout(title_col)
        header.addStretch()

        style_label = QLabel()
        style_label.setProperty("role", "section")
        style_mono_section(style_label)
        i18n.bind(style_label.setText, "history.header.style")
        header.addWidget(style_label)
        self._style_combo = QComboBox()
        self._style_combo.setMinimumWidth(180)
        self._style_combo.currentIndexChanged.connect(self._on_style_combo_changed)
        header.addWidget(self._style_combo)

        self._settings_btn = QPushButton()
        self._settings_btn.clicked.connect(self.show_settings)
        i18n.bind(self._settings_btn.setText, "history.header.settings")
        header.addWidget(self._settings_btn)
        layout.addLayout(header)

        # History list — QScrollArea inside a card-styled QFrame. We let
        # QVBoxLayout + QLabel.wordWrap compute heights naturally; no manual
        # elidedText, no sizeHint patching.
        self._history_card = QFrame()
        self._history_card.setObjectName("historyCard")
        card_layout = QVBoxLayout(self._history_card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("historyScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._history_container = QWidget()
        self._history_container.setObjectName("historyContainer")
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(8)

        self._scroll.setWidget(self._history_container)
        card_layout.addWidget(self._scroll)
        layout.addWidget(self._history_card, 1)

        # Empty state
        self._empty_label = QLabel()
        i18n.bind(self._empty_label.setText, "history.empty")
        self._empty_label.setProperty("role", "muted")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("padding: 40px;")
        layout.addWidget(self._empty_label, 1)

        # Action row. Copy is the more common action (primary look), but
        # both buttons sit next to each other and should occupy the same
        # space — Qt's default sizing renders the primary button wider
        # because its QSS adds extra padding, which made the pair look
        # lopsided. Pinning them to the same minimum width keeps the
        # primary styling but evens out the geometry.
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self._copy_btn = QPushButton()
        self._copy_btn.setProperty("role", "primary")
        i18n.bind(self._copy_btn.setText, "history.action.copy")
        self._insert_btn = QPushButton()
        i18n.bind(self._insert_btn.setText, "history.action.insert")
        for btn in (self._copy_btn, self._insert_btn):
            btn.setMinimumWidth(140)
        self._delete_btn = QPushButton()
        self._delete_btn.setProperty("role", "danger")
        i18n.bind(self._delete_btn.setText, "history.action.delete")
        actions.addWidget(self._copy_btn)
        actions.addWidget(self._insert_btn)
        actions.addStretch()
        actions.addWidget(self._delete_btn)
        self._clear_btn = QPushButton()
        self._clear_btn.setProperty("role", "danger")
        i18n.bind(self._clear_btn.setText, "history.action.clear_all")
        actions.addWidget(self._clear_btn)
        layout.addLayout(actions)

        self._copy_btn.clicked.connect(self._on_copy)
        self._insert_btn.clicked.connect(self._on_insert)
        self._delete_btn.clicked.connect(self._on_delete)
        self._clear_btn.clicked.connect(self._on_clear)

        return page

    def history_widget(self) -> QWidget:
        return self._history_card

    def refresh(self) -> None:
        # German-style thousand separator (1.234.567) — kept regardless of UI
        # language because the underlying numbers are conventionally written
        # this way in TypeStream's primary user community.
        today = f"{self._stats.today:,}".replace(",", ".")
        total = f"{self._stats.total:,}".replace(",", ".")
        self._stats_label.setText(
            i18n.t("history.stats_line", today=today, total=total)
        )

        while self._history_layout.count():
            item = self._history_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

        entries = self._history.all()
        for i, entry in enumerate(entries):
            row = HistoryRow(i, entry)
            row.clicked.connect(self._select_row)
            row.double_clicked.connect(self._on_row_double_clicked)
            self._history_layout.addWidget(row)
            self._rows.append(row)

        if entries:
            self._selected_index = 0
            self._rows[0].set_selected(True)
            self._scroll.verticalScrollBar().setValue(0)
            self._history_card.show()
            self._empty_label.hide()
            self._copy_btn.setEnabled(True)
            self._insert_btn.setEnabled(True)
            self._delete_btn.setEnabled(True)
            self._clear_btn.setEnabled(True)
        else:
            self._selected_index = -1
            self._history_card.hide()
            self._empty_label.show()
            self._copy_btn.setEnabled(False)
            self._insert_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._clear_btn.setEnabled(False)

        # Keep statistics page live whenever history changes
        self._settings_view.update_stats(entries)

    def _select_row(self, index: int) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if self._selected_index == index:
            return
        if 0 <= self._selected_index < len(self._rows):
            self._rows[self._selected_index].set_selected(False)
        self._rows[index].set_selected(True)
        self._selected_index = index

    def _on_row_double_clicked(self, index: int) -> None:
        self._select_row(index)
        self._on_copy()

    def _selected_entry(self) -> HistoryEntry | None:
        entries = self._history.all()
        if 0 <= self._selected_index < len(entries):
            return entries[self._selected_index]
        return None

    def _on_copy(self) -> None:
        e = self._selected_entry()
        if e is not None:
            self.copy_requested.emit(e.text)

    def _on_insert(self) -> None:
        e = self._selected_entry()
        if e is not None:
            self.insert_requested.emit(e.text)

    def _on_delete(self) -> None:
        if self._selected_index >= 0:
            self._history.remove(self._selected_index)
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
