from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QPushButton

import mouse

DISPLAY_NAMES = {
    "mouse:left": "Maus Links",
    "mouse:right": "Maus Rechts",
    "mouse:middle": "Maus Mitte",
    "mouse:x": "Maustaste 4 (X1)",
    "mouse:x2": "Maustaste 5 (X2)",
}

CAPTURABLE_MOUSE_BUTTONS = ("middle", "x", "x2")


def display_label(hotkey: str) -> str:
    if not hotkey:
        return "(kein Hotkey)"
    if hotkey in DISPLAY_NAMES:
        return DISPLAY_NAMES[hotkey]
    return "+".join(part.capitalize() for part in hotkey.split("+"))


def _qt_key_to_keyboard_name(key: int, text: str) -> str | None:
    if Qt.Key.Key_A.value <= key <= Qt.Key.Key_Z.value:
        return chr(ord("a") + (key - Qt.Key.Key_A.value))
    if Qt.Key.Key_0.value <= key <= Qt.Key.Key_9.value:
        return chr(ord("0") + (key - Qt.Key.Key_0.value))
    if Qt.Key.Key_F1.value <= key <= Qt.Key.Key_F35.value:
        return f"f{key - Qt.Key.Key_F1.value + 1}"
    if text and len(text) == 1 and text.isascii() and text.isalnum():
        return text.lower()
    special = {
        Qt.Key.Key_Space.value: "space",
        Qt.Key.Key_Tab.value: "tab",
        Qt.Key.Key_Return.value: "enter",
        Qt.Key.Key_Enter.value: "enter",
        Qt.Key.Key_Backspace.value: "backspace",
        Qt.Key.Key_Insert.value: "insert",
        Qt.Key.Key_Delete.value: "delete",
        Qt.Key.Key_Home.value: "home",
        Qt.Key.Key_End.value: "end",
        Qt.Key.Key_PageUp.value: "page up",
        Qt.Key.Key_PageDown.value: "page down",
        Qt.Key.Key_Up.value: "up",
        Qt.Key.Key_Down.value: "down",
        Qt.Key.Key_Left.value: "left",
        Qt.Key.Key_Right.value: "right",
        Qt.Key.Key_Plus.value: "plus",
        Qt.Key.Key_Minus.value: "minus",
        Qt.Key.Key_Comma.value: ",",
        Qt.Key.Key_Period.value: ".",
        Qt.Key.Key_Semicolon.value: ";",
    }
    return special.get(key)


class HotkeyCaptureButton(QPushButton):
    captured = pyqtSignal(str)
    _captured_internal = pyqtSignal(str)

    def __init__(self, current: str = "", allow_mouse: bool = True, parent=None):
        super().__init__(parent)
        self._current = current
        self._allow_mouse = allow_mouse
        self._capturing = False
        self._mouse_handles: list = []
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self._toggle_capture)
        self._captured_internal.connect(
            self._on_capture_done, Qt.ConnectionType.QueuedConnection
        )
        self._refresh_label()

    def value(self) -> str:
        return self._current

    def setValue(self, hotkey: str) -> None:
        self._current = hotkey
        self._refresh_label()

    def _refresh_label(self) -> None:
        if self._capturing:
            self.setText("Drücke jetzt eine Taste oder Maustaste …  (Esc = Abbrechen)")
        else:
            self.setText(display_label(self._current))

    def _toggle_capture(self) -> None:
        if self._capturing:
            self._stop_capture()
        else:
            self._start_capture()

    def _start_capture(self) -> None:
        self._capturing = True
        self._refresh_label()
        self.setFocus()
        self.grabKeyboard()
        if self._allow_mouse:
            for button in CAPTURABLE_MOUSE_BUTTONS:
                try:
                    handle = mouse.on_button(
                        lambda b=button: self._captured_internal.emit(f"mouse:{b}"),
                        buttons=(button,),
                        types=("down",),
                    )
                    self._mouse_handles.append(handle)
                except Exception:
                    pass

    def _stop_capture(self) -> None:
        self._capturing = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        for h in self._mouse_handles:
            try:
                mouse.unhook(h)
            except (KeyError, ValueError):
                pass
        self._mouse_handles.clear()
        self._refresh_label()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key.Key_Escape.value:
            self._stop_capture()
            return
        if key in (
            Qt.Key.Key_Control.value,
            Qt.Key.Key_Alt.value,
            Qt.Key.Key_Shift.value,
            Qt.Key.Key_Meta.value,
            Qt.Key.Key_AltGr.value,
        ):
            return
        parts: list[str] = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("windows")
        name = _qt_key_to_keyboard_name(key, event.text())
        if not name:
            return
        parts.append(name)
        hotkey = "+".join(parts)
        self._current = hotkey
        self._stop_capture()
        self.captured.emit(hotkey)

    def _on_capture_done(self, hotkey: str) -> None:
        if not self._capturing:
            return
        self._current = hotkey
        self._stop_capture()
        self.captured.emit(hotkey)

    def hideEvent(self, event):
        if self._capturing:
            self._stop_capture()
        super().hideEvent(event)
