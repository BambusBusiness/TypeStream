from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


class PulsingDot(QWidget):
    """Round indicator whose opacity loops between 1.0 and a low value."""

    def __init__(
        self,
        color: QColor | str = "#EF4444",
        diameter: int = 12,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._color = QColor(color)
        self._opacity = 1.0
        self.setFixedSize(diameter + 4, diameter + 4)
        self._diameter = diameter

        self._anim = QPropertyAnimation(self, b"opacity", self)
        self._anim.setDuration(1100)
        self._anim.setStartValue(1.0)
        self._anim.setKeyValueAt(0.5, 0.30)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    opacity = pyqtProperty(float, get_opacity, set_opacity)

    def set_color(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self.update()

    def start_pulse(self) -> None:
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._anim.start()

    def stop_pulse(self) -> None:
        self._anim.stop()
        self._opacity = 1.0
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlphaF(max(0.0, min(1.0, self._opacity)))
        painter.setBrush(c)
        painter.setPen(Qt.PenStyle.NoPen)
        d = self._diameter
        x = (self.width() - d) // 2
        y = (self.height() - d) // 2
        painter.drawEllipse(x, y, d, d)
        painter.end()
