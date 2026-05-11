from __future__ import annotations

import logging
import threading
import time

import pyautogui
import pyperclip

pyautogui.FAILSAFE = False

log = logging.getLogger("typestream.inserter")

CLIPBOARD_RESTORE_DELAY_S = 0.4


class TextInserter:
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
