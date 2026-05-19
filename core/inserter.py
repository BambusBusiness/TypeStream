from __future__ import annotations

import logging
import threading
import time

import keyboard
import pyperclip

log = logging.getLogger("typestream.inserter")

CLIPBOARD_RESTORE_DELAY_S = 0.4
# When the paste hotkey itself uses modifiers (e.g. Ctrl+Alt+V), the user is
# typically still holding them at the moment our handler runs. We wait this
# long for them to release naturally before sending Ctrl+V, then force the
# modifiers up as a safety net for users who keep them pinned. Without this,
# our synthetic Ctrl+V combines with the user's Alt to become Ctrl+Alt+V,
# which doesn't paste in any normal app.
_MODIFIER_RELEASE_TIMEOUT_S = 0.35
_MODIFIER_POLL_INTERVAL_S = 0.02
_MODIFIERS = ("ctrl", "alt", "shift", "windows")


def _wait_for_modifier_release(timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not any(keyboard.is_pressed(m) for m in _MODIFIERS):
            return
        time.sleep(_MODIFIER_POLL_INTERVAL_S)


def _force_release_modifiers() -> None:
    for mod in _MODIFIERS:
        try:
            keyboard.release(mod)
        except (ValueError, KeyError):
            pass


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
            _wait_for_modifier_release(_MODIFIER_RELEASE_TIMEOUT_S)
            _force_release_modifiers()
            time.sleep(0.03)
        try:
            keyboard.send("ctrl+v")
        except Exception:
            log.exception("keyboard.send('ctrl+v') failed")
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
