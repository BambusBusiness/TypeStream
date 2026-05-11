from __future__ import annotations

import logging
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

log = logging.getLogger("typestream.sounds")

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
START_PATH = ASSETS_DIR / "start.mp3"
STOP_PATH = ASSETS_DIR / "stop.mp3"
WARNING_PATH = ASSETS_DIR / "warning.mp3"

_initialized = False
_start_sound: "pygame.mixer.Sound | None" = None
_stop_sound: "pygame.mixer.Sound | None" = None
_warning_sound: "pygame.mixer.Sound | None" = None
_volume: float = 1.0


def init() -> None:
    global _initialized, _start_sound, _stop_sound, _warning_sound
    if _initialized:
        return
    _initialized = True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        log.exception("pygame.mixer.init() failed — sound feedback disabled")
        return
    for attr, path in (
        ("_start_sound", START_PATH),
        ("_stop_sound", STOP_PATH),
        ("_warning_sound", WARNING_PATH),
    ):
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(_volume)
            globals()[attr] = sound
            log.info("Pre-loaded %s from %s", attr, path)
        except (pygame.error, FileNotFoundError, OSError):
            log.exception("Failed to preload %s", path)


def set_volume(volume: float) -> None:
    global _volume
    _volume = max(0.0, min(1.0, volume))
    for sound in (_start_sound, _stop_sound, _warning_sound):
        if sound is not None:
            sound.set_volume(_volume)


def _play(sound: "pygame.mixer.Sound | None") -> None:
    if sound is None or _volume <= 0.0:
        return
    try:
        sound.play()
    except pygame.error:
        log.exception("Sound playback failed")


def play_start() -> None:
    _play(_start_sound)


def play_stop() -> None:
    _play(_stop_sound)


def play_warning() -> None:
    _play(_warning_sound)
