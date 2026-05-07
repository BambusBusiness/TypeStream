from __future__ import annotations

from typing import Callable

import keyboard
import mouse

MOUSE_PREFIX = "mouse:"
MOUSE_BUTTONS = {"left", "right", "middle", "x", "x2"}


def is_mouse_hotkey(hotkey: str) -> bool:
    return hotkey.startswith(MOUSE_PREFIX)


def _mouse_button(hotkey: str) -> str:
    button = hotkey[len(MOUSE_PREFIX) :].strip().lower()
    if button not in MOUSE_BUTTONS:
        raise ValueError(f"Unknown mouse button: {button}")
    return button


class HotkeyManager:
    def __init__(self):
        self._hotkey_handles: list = []
        self._hook_handles: list = []
        self._mouse_handles: list = []

    def register_record_ptt(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        if is_mouse_hotkey(hotkey):
            button = _mouse_button(hotkey)
            h_down = mouse.on_button(on_press, buttons=(button,), types=("down",))
            h_up = mouse.on_button(on_release, buttons=(button,), types=("up",))
            self._mouse_handles.extend([h_down, h_up])
            return
        if "+" in hotkey:
            raise ValueError("PTT requires a single key (no '+').")
        h_press = keyboard.on_press_key(hotkey, lambda e: on_press())
        h_release = keyboard.on_release_key(hotkey, lambda e: on_release())
        self._hook_handles.extend([h_press, h_release])

    def register_record_toggle(self, hotkey: str, callback: Callable[[], None]) -> None:
        if is_mouse_hotkey(hotkey):
            button = _mouse_button(hotkey)
            h = mouse.on_button(callback, buttons=(button,), types=("down",))
            self._mouse_handles.append(h)
            return
        h = keyboard.add_hotkey(hotkey, callback)
        self._hotkey_handles.append(h)

    def register_paste(self, hotkey: str, callback: Callable[[], None]) -> None:
        if is_mouse_hotkey(hotkey):
            button = _mouse_button(hotkey)
            h = mouse.on_button(callback, buttons=(button,), types=("down",))
            self._mouse_handles.append(h)
            return
        h = keyboard.add_hotkey(hotkey, callback)
        self._hotkey_handles.append(h)

    def unregister_all(self) -> None:
        for h in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(h)
            except (KeyError, ValueError):
                pass
        for h in self._hook_handles:
            try:
                keyboard.unhook(h)
            except (KeyError, ValueError):
                pass
        for h in self._mouse_handles:
            try:
                mouse.unhook(h)
            except (KeyError, ValueError):
                pass
        self._hotkey_handles.clear()
        self._hook_handles.clear()
        self._mouse_handles.clear()
