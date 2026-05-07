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

_initialized = False
_start_sound: "pygame.mixer.Sound | None" = None
_stop_sound: "pygame.mixer.Sound | None" = None


def init() -> None:
    global _initialized, _start_sound, _stop_sound
    if _initialized:
        return
    _initialized = True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        log.exception("pygame.mixer.init() failed — sound feedback disabled")
        return
    try:
        _start_sound = pygame.mixer.Sound(str(START_PATH))
        log.info("Pre-loaded start sound from %s", START_PATH)
    except (pygame.error, FileNotFoundError, OSError):
        log.exception("Failed to preload %s", START_PATH)
    try:
        _stop_sound = pygame.mixer.Sound(str(STOP_PATH))
        log.info("Pre-loaded stop sound from %s", STOP_PATH)
    except (pygame.error, FileNotFoundError, OSError):
        log.exception("Failed to preload %s", STOP_PATH)


def _play(sound: "pygame.mixer.Sound | None") -> None:
    if sound is None:
        return
    try:
        sound.play()
    except pygame.error:
        log.exception("Sound playback failed")


def play_start() -> None:
    _play(_start_sound)


def play_stop() -> None:
    _play(_stop_sound)
