from __future__ import annotations

import logging
import sys
import threading
import time

import pyautogui
import pyperclip

pyautogui.FAILSAFE = False

log = logging.getLogger("typestream.inserter")

CLIPBOARD_RESTORE_DELAY_S = 0.4


def has_editable_focus() -> bool:
    """Best-effort: does the foreground window currently have a text caret?

    On Windows a blinking caret almost always means a text-editable control
    is focused (Edit/RichEdit/most web inputs). We use that as a heuristic
    to skip the auto-paste when no field is ready. Returns True on non-Windows
    or when the API call fails (i.e. we don't block the paste pessimistically)."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        from ctypes import wintypes

        class GUITHREADINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        user32 = ctypes.windll.user32
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            return True
        return bool(info.hwndCaret)
    except Exception:
        log.debug("has_editable_focus check failed", exc_info=True)
        return True


class TextInserter:
    def has_editable_focus(self) -> bool:
        return has_editable_focus()

    def insert_at_cursor(self, text: str, release_modifiers: bool = True) -> bool:
        try:
            previous = pyperclip.paste()
        except Exception:
            previous = None
        try:
            pyperclip.copy(text)
        except Exception:
            return False
        if release_modifiers:
            for mod in ("ctrl", "alt", "shift", "win"):
                try:
                    pyautogui.keyUp(mod)
                except Exception:
                    pass
            time.sleep(0.05)
        try:
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            return False
        if previous is not None and previous != text:
            threading.Thread(
                target=self._restore_clipboard,
                args=(previous,),
                daemon=True,
            ).start()
        return True

    def copy_to_clipboard(self, text: str) -> bool:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    @staticmethod
    def _restore_clipboard(previous: str) -> None:
        time.sleep(CLIPBOARD_RESTORE_DELAY_S)
        try:
            pyperclip.copy(previous)
        except Exception:
            pass
