from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QWidget


INTER_STACK = (
    "'Inter', 'Inter Variable', 'Segoe UI Variable Display', "
    "'Segoe UI', system-ui, sans-serif"
)
SERIF_STACK = "'Calistoga', 'Georgia', 'Cambria', 'Times New Roman', serif"
MONO_STACK = (
    "'JetBrains Mono', 'Cascadia Mono', 'Consolas', "
    "'Liberation Mono', 'Courier New', monospace"
)


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_hover: str
    surface_elevated: str
    input_bg: str
    border: str
    border_hover: str
    fg: str
    fg_muted: str
    fg_subtle: str
    primary: str
    primary_hover: str
    primary_fg: str
    accent: str
    accent_hover: str
    danger: str
    danger_hover: str
    danger_bg: str
    recording: str
    recording_dot: str
    gradient_start: str
    gradient_end: str
    gradient_start_hover: str
    gradient_end_hover: str
    shadow_alpha: int
    shadow_blur: int


DARK = Palette(
    name="dark",
    bg="#0F172A",
    surface="#1E293B",
    surface_hover="#273449",
    surface_elevated="#1A2438",
    input_bg="#0F172A",
    border="#1E293B",
    border_hover="#334155",
    fg="#FFFFFF",
    fg_muted="#94A3B8",
    fg_subtle="#64748B",
    primary="#0052FF",
    primary_hover="#1A66FF",
    primary_fg="#FFFFFF",
    accent="#6D28D9",
    accent_hover="#7C3AED",
    danger="#F87171",
    danger_hover="#EF4444",
    danger_bg="#3A1A2A",
    recording="#6D28D9",
    recording_dot="#EF4444",
    gradient_start="#0052FF",
    gradient_end="#6D28D9",
    gradient_start_hover="#1A66FF",
    gradient_end_hover="#7C3AED",
    shadow_alpha=0,
    shadow_blur=0,
)


LIGHT = Palette(
    name="light",
    bg="#FAFAFA",
    surface="#FFFFFF",
    surface_hover="#F1F5F9",
    surface_elevated="#FFFFFF",
    input_bg="#FFFFFF",
    border="#E2E8F0",
    border_hover="#CBD5E1",
    fg="#0F172A",
    fg_muted="#64748B",
    fg_subtle="#94A3B8",
    primary="#0052FF",
    primary_hover="#1A66FF",
    primary_fg="#FFFFFF",
    accent="#6D28D9",
    accent_hover="#7C3AED",
    danger="#DC2626",
    danger_hover="#B91C1C",
    danger_bg="#FEE2E2",
    recording="#6D28D9",
    recording_dot="#DC2626",
    gradient_start="#0052FF",
    gradient_end="#6D28D9",
    gradient_start_hover="#1A66FF",
    gradient_end_hover="#7C3AED",
    shadow_alpha=28,
    shadow_blur=24,
)


PALETTES: dict[str, Palette] = {"dark": DARK, "light": LIGHT}


def get_palette(name: str) -> Palette:
    return PALETTES.get(name, DARK)


def style_serif_title(label: QLabel, point_size: int = 28) -> None:
    font = label.font()
    font.setFamilies(["Calistoga", "Georgia", "Cambria", "Times New Roman"])
    font.setStyleHint(QFont.StyleHint.Serif)
    font.setPointSize(point_size)
    font.setWeight(QFont.Weight.Normal)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98.0)
    label.setFont(font)


def style_mono_section(label: QLabel, point_size: int = 8) -> None:
    font = label.font()
    font.setFamilies(
        ["JetBrains Mono", "Cascadia Mono", "Consolas", "Liberation Mono", "Courier New"]
    )
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    font.setPointSize(point_size)
    font.setWeight(QFont.Weight.Bold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
    label.setFont(font)


def apply_card_shadow(widget: QWidget, palette: Palette) -> None:
    if palette.shadow_alpha <= 0:
        widget.setGraphicsEffect(None)
        return
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(palette.shadow_blur)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(15, 23, 42, palette.shadow_alpha))
    widget.setGraphicsEffect(shadow)


def build_qss(p: Palette) -> str:
    gradient = (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        f"stop:0 {p.gradient_start}, stop:1 {p.gradient_end})"
    )
    gradient_hover = (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        f"stop:0 {p.gradient_start_hover}, stop:1 {p.gradient_end_hover})"
    )
    return f"""
* {{
    font-family: {INTER_STACK};
    font-size: 13px;
    color: {p.fg};
}}

QMainWindow {{
    background-color: {p.bg};
}}

QDialog {{
    background-color: {p.bg};
}}

QWidget#appCentral {{
    background-color: {p.bg};
}}

QLabel {{
    background: transparent;
    color: {p.fg};
}}

QLabel[role="muted"] {{
    color: {p.fg_muted};
}}

QLabel[role="title"] {{
    font-family: {SERIF_STACK};
    color: {p.fg};
}}

QLabel[role="section"] {{
    font-family: {MONO_STACK};
    font-weight: 700;
    color: {p.fg_subtle};
    padding: 22px 0 8px 0;
}}

QPushButton {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 12px;
    padding: 11px 20px;
    color: {p.fg};
    font-weight: 500;
    min-height: 24px;
}}

QPushButton:hover {{
    background: {p.surface_hover};
    border-color: {p.border_hover};
}}

QPushButton:pressed {{
    background: {p.border};
}}

QPushButton:focus {{
    outline: none;
    border-color: {p.primary};
}}

QPushButton:disabled {{
    background: {p.surface};
    color: {p.fg_subtle};
    border-color: {p.border};
}}

QPushButton[role="primary"] {{
    background: {gradient};
    color: {p.primary_fg};
    border: none;
    font-weight: 600;
    padding: 12px 22px;
    min-height: 26px;
}}

QPushButton[role="primary"]:hover {{
    background: {gradient_hover};
}}

QPushButton[role="primary"]:pressed {{
    background: {gradient};
}}

QPushButton[role="primary"]:disabled {{
    background: {p.surface};
    color: {p.fg_subtle};
}}

QPushButton[role="danger"] {{
    color: {p.danger};
    background: transparent;
}}

QPushButton[role="danger"]:hover {{
    background: {p.danger_bg};
    border-color: {p.danger};
    color: {p.danger_hover};
}}

QPushButton[role="recording"] {{
    background: {gradient};
    color: {p.primary_fg};
    border: none;
    font-weight: 600;
}}

QPushButton[role="recording"]:hover {{
    background: {gradient_hover};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
    background: {p.input_bg};
    border: 2px solid {p.border};
    border-radius: 12px;
    padding: 11px 13px;
    color: {p.fg};
    selection-background-color: {p.primary};
    selection-color: {p.primary_fg};
    min-height: 24px;
}}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QComboBox:hover, QPlainTextEdit:hover {{
    border-color: {p.border_hover};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus {{
    border-color: {p.primary};
}}

QLineEdit::placeholder {{
    color: {p.fg_subtle};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 18px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {p.fg_muted};
    width: 0;
    height: 0;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.fg_muted};
    width: 0;
    height: 0;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 12px;
    width: 22px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.fg_muted};
    width: 0;
    height: 0;
}}

QComboBox QAbstractItemView {{
    background: {p.surface_elevated};
    border: 1px solid {p.border_hover};
    border-radius: 12px;
    padding: 6px;
    selection-background-color: {p.primary};
    selection-color: {p.primary_fg};
    color: {p.fg};
    outline: none;
}}

QListWidget {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 12px;
    padding: 10px;
    outline: none;
}}

QListWidget::item {{
    background: {p.surface_elevated};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 16px 18px;
    margin: 5px 2px;
    color: {p.fg};
}}

QListWidget::item:selected {{
    background: {p.surface_elevated};
    border: 1px solid {p.primary};
    color: {p.fg};
}}

QListWidget::item:hover {{
    background: {p.surface_hover};
    border-color: {p.border_hover};
}}

QCheckBox {{
    spacing: 12px;
    background: transparent;
    color: {p.fg};
    padding: 4px 0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {p.border_hover};
    border-radius: 6px;
    background: {p.input_bg};
}}

QCheckBox::indicator:hover {{
    border-color: {p.primary};
}}

QCheckBox::indicator:checked {{
    background: {gradient};
    border: none;
}}

QFormLayout > QLabel, QFormLayout QLabel {{
    color: {p.fg_muted};
    font-weight: 500;
}}

QMenu {{
    background: {p.surface_elevated};
    border: 1px solid {p.border_hover};
    border-radius: 12px;
    padding: 8px;
    color: {p.fg};
}}

QMenu::item {{
    padding: 10px 22px;
    border-radius: 8px;
    color: {p.fg};
}}

QMenu::item:selected {{
    background: {gradient};
    color: {p.primary_fg};
}}

QMenu::separator {{
    height: 1px;
    background: {p.border};
    margin: 6px 10px;
}}

QToolTip {{
    background: {p.surface_elevated};
    color: {p.fg};
    border: 1px solid {p.border_hover};
    border-radius: 8px;
    padding: 8px 12px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: {p.border_hover};
    border-radius: 4px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p.primary};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: transparent;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}}

QScrollBar::handle:horizontal {{
    background: {p.border_hover};
    border-radius: 4px;
    min-width: 28px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {p.primary};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: transparent;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
"""


APP_QSS = build_qss(DARK)
