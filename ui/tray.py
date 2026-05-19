from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from core.i18n import i18n
from core.styles import Style, all_styles


def _solid_circle_icon(color: QColor) -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(8, 8, 48, 48)
    p.end()
    return QIcon(pix)


def _load_svg_icon(svg_path: Path) -> QIcon | None:
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        return None
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    return icon


def _assets_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets"


def _load_idle_icon() -> QIcon:
    # Prefer the SVG: QSvgRenderer produces a crisp QIcon with multiple
    # explicit pixmap sizes, which Windows picks the right one from for the
    # taskbar/Alt-Tab/title-bar (all of which use different pixel sizes per
    # DPI scale). A single-size icon.ico looks blurry whenever Windows wants
    # anything bigger than 16x16.
    icon_dir = _assets_dir()
    svg_path = icon_dir / "icon.svg"
    if svg_path.exists():
        svg_icon = _load_svg_icon(svg_path)
        if svg_icon is not None:
            return svg_icon
    for name in ("icon.png", "icon.ico"):
        path = icon_dir / name
        if path.exists():
            return QIcon(str(path))
    return _solid_circle_icon(QColor("#3a86ff"))


def load_app_icon() -> QIcon:
    return _load_idle_icon()


class TrayIcon(QSystemTrayIcon):
    open_history = pyqtSignal()
    open_settings = pyqtSignal()
    copy_last = pyqtSignal()
    quit_app = pyqtSignal()
    style_changed = pyqtSignal(str)
    update_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._idle_icon = _load_idle_icon()
        self._recording_icon = _solid_circle_icon(QColor("#ef233c"))
        self._busy_icon = _solid_circle_icon(QColor("#ffb703"))

        self.setIcon(self._idle_icon)
        i18n.bind(self.setToolTip, "app.tray.tooltip_idle")

        self._menu = QMenu()
        act_history = QAction(self)
        act_settings = QAction(self)
        act_copy = QAction(self)
        act_quit = QAction(self)
        i18n.bind(act_history.setText, "tray.menu.open_history")
        i18n.bind(act_settings.setText, "tray.menu.settings")
        i18n.bind(act_copy.setText, "tray.menu.copy_last")
        i18n.bind(act_quit.setText, "tray.menu.quit")

        self._style_menu = QMenu(self._menu)
        i18n.bind(self._style_menu.setTitle, "tray.menu.style")
        self._style_group = QActionGroup(self)
        self._style_group.setExclusive(True)
        self._style_actions: dict[str, QAction] = {}

        self._update_action = QAction(self)
        self._update_version: str = ""
        self._update_action.setVisible(False)
        self._update_action.triggered.connect(self.update_clicked.emit)
        i18n.language_changed.connect(self._refresh_dynamic_labels)
        self._update_separator = self._menu.addSeparator()
        self._update_separator.setVisible(False)
        self._menu.addAction(self._update_action)
        self._menu.addAction(act_history)
        self._menu.addAction(act_settings)
        self._menu.addSeparator()
        self._menu.addMenu(self._style_menu)
        self._menu.addSeparator()
        self._menu.addAction(act_copy)
        self._menu.addSeparator()
        self._menu.addAction(act_quit)
        self.setContextMenu(self._menu)

        act_history.triggered.connect(self.open_history.emit)
        act_settings.triggered.connect(self.open_settings.emit)
        act_copy.triggered.connect(self.copy_last.emit)
        act_quit.triggered.connect(self.quit_app.emit)

        self.activated.connect(self._on_activated)

    def set_update_available(self, version: str | None) -> None:
        if version:
            self._update_version = version
            self._update_action.setText(
                i18n.t("tray.menu.update_install", version=version)
            )
            self._update_action.setVisible(True)
            self._update_separator.setVisible(True)
        else:
            self._update_version = ""
            self._update_action.setVisible(False)
            self._update_separator.setVisible(False)

    def _refresh_dynamic_labels(self) -> None:
        if self._update_version:
            self._update_action.setText(
                i18n.t("tray.menu.update_install", version=self._update_version)
            )

    def _on_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_history.emit()

    def update_styles(self, styles: list[Style], active_key: str) -> None:
        for action in list(self._style_actions.values()):
            self._style_group.removeAction(action)
            self._style_menu.removeAction(action)
        self._style_actions.clear()

        for style in styles:
            action = QAction(style.label, self)
            action.setCheckable(True)
            action.setChecked(style.key == active_key)
            action.triggered.connect(lambda _checked, k=style.key: self.style_changed.emit(k))
            self._style_group.addAction(action)
            self._style_menu.addAction(action)
            self._style_actions[style.key] = action

    def set_active_style(self, key: str) -> None:
        for k, action in self._style_actions.items():
            action.setChecked(k == key)

    def set_state_idle(self) -> None:
        self.setIcon(self._idle_icon)
        self.setToolTip(i18n.t("app.tray.tooltip_idle"))

    def set_state_recording(self) -> None:
        self.setIcon(self._recording_icon)
        self.setToolTip(i18n.t("app.tray.tooltip_recording"))

    def set_state_busy(self) -> None:
        self.setIcon(self._busy_icon)
        self.setToolTip(i18n.t("app.tray.tooltip_busy"))

    def notify(self, message: str, level: str = "info") -> None:
        icon = {
            "info": QSystemTrayIcon.MessageIcon.Information,
            "warn": QSystemTrayIcon.MessageIcon.Warning,
            "error": QSystemTrayIcon.MessageIcon.Critical,
        }.get(level, QSystemTrayIcon.MessageIcon.Information)
        self.showMessage("TypeStream", message, icon, 3000)
