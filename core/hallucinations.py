from __future__ import annotations

import re

# Bekannte Whisper-Halluzinationen bei Stille / leiser Aufnahme.
# Lowercase, ohne Satzzeichen am Ende — Vergleich erfolgt normalisiert.
SILENCE_PHRASES = (
    "vielen dank fürs zuschauen",
    "vielen dank für's zuschauen",
    "vielen dank für ihre aufmerksamkeit",
    "danke fürs zuschauen",
    "danke fürs zusehen",
    "untertitel von stephanie geiges",
    "untertitel im auftrag des zdf",
    "untertitelung des zdf",
    "untertitel der amara.org-community",
    "thanks for watching",
    "thank you for watching",
    "thanks for watching!",
    "subtitles by the amara.org community",
    "subtítulos por la comunidad de amara.org",
    "tschüss",
    "ciao",
    "bis zum nächsten mal",
)


def _normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[^\wäöüß ]+", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def is_likely_silence(text: str, prompt: str = "") -> bool:
    if not text or not text.strip():
        return True
    norm = _normalize(text)
    if not norm:
        return True
    if prompt:
        prompt_norm = _normalize(prompt)
        if prompt_norm and (norm == prompt_norm or norm in prompt_norm):
            return True
    for phrase in SILENCE_PHRASES:
        if norm == phrase or norm.startswith(phrase) or norm.endswith(phrase):
            return True
    return False
