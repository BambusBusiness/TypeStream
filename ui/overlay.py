from __future__ import annotations

import sys

from PyQt6.QtCore import QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.components import PulsingDot
from ui.style import DARK, INTER_STACK, Palette


PILL_BG = "#0F172A"
PILL_FG = "#FFFFFF"
PILL_RADIUS = 18
PILL_INSET = 0

# Win32 DWM constants for disabling Win11's automatic window decoration
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWCP_DONOTROUND = 1
_DWMWA_COLOR_NONE = 0xFFFFFFFE


def _disable_win11_window_decoration(widget: QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(widget.winId()))
        dwmapi = ctypes.windll.dwmapi

        corner = wintypes.DWORD(_DWMWCP_DONOTROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            wintypes.DWORD(_DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(corner),
            ctypes.sizeof(corner),
        )

        color = wintypes.DWORD(_DWMWA_COLOR_NONE)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            wintypes.DWORD(_DWMWA_BORDER_COLOR),
            ctypes.byref(color),
            ctypes.sizeof(color),
        )
    except (OSError, AttributeError):
        pass


class RecordingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordingOverlayRoot")
        self._palette: Palette = DARK
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_with_fade)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._dot = PulsingDot(self._palette.recording_dot, diameter=12)
        self._text = QLabel("Aufnahme")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            20 + PILL_INSET,
            12 + PILL_INSET,
            22 + PILL_INSET,
            12 + PILL_INSET,
        )
        layout.setSpacing(12)
        layout.addWidget(self._dot)
        layout.addWidget(self._text)

        self.setStyleSheet(
            f"""
            QWidget#recordingOverlayRoot {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {PILL_FG};
                font-family: {INTER_STACK};
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )

        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(180)
        self.setWindowOpacity(0.0)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        _disable_win11_window_decoration(self)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(PILL_BG))
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(PILL_INSET, PILL_INSET, -PILL_INSET, -PILL_INSET)
        painter.drawRoundedRect(rect, PILL_RADIUS, PILL_RADIUS)

    def apply_palette(self, palette: Palette) -> None:
        self._palette = palette
        self._dot.set_color(palette.recording_dot)

    def _set_text(self, text: str) -> None:
        self._text.setText(text)
        layout = self.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()
        self.resize(self.sizeHint())
        self.update()

    def _position(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        geom = screen.availableGeometry()
        x = geom.x() + (geom.width() - self.width()) // 2
        y = geom.y() + geom.height() - self.height() - 80
        self.move(x, y)

    def _fade_in(self) -> None:
        self._fade.stop()
        try:
            self._fade.finished.disconnect()
        except TypeError:
            pass
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

    def show_recording(self) -> None:
        self._hide_timer.stop()
        self._dot.set_color(self._palette.recording_dot)
        self._dot.start_pulse()
        self._set_text("Aufnahme")
        self._position()
        self.show()
        self.raise_()
        self._fade_in()

    def show_busy(self) -> None:
        self._hide_timer.stop()
        self._dot.set_color(self._palette.recording)
        self._dot.start_pulse()
        self._set_text("Transkribiere …")
        self._position()
        self.show()
        self.raise_()
        self._fade_in()

    def show_message(self, text: str, level: str = "warn", duration_ms: int = 2200) -> None:
        self._hide_timer.stop()
        accent = {
            "warn": self._palette.accent,
            "error": self._palette.danger_hover,
            "info": self._palette.primary,
        }.get(level, self._palette.accent)
        self._dot.set_color(accent)
        self._dot.stop_pulse()
        self._set_text(text)
        self._position()
        self.show()
        self.raise_()
        self._fade_in()
        self._hide_timer.start(duration_ms)

    def hide_with_fade(self) -> None:
        self._hide_timer.stop()
        self._dot.stop_pulse()
        self._fade.stop()
        try:
            self._fade.finished.disconnect()
        except TypeError:
            pass
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.hide)
        self._fade.start()
