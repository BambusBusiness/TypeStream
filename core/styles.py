from __future__ import annotations

from dataclasses import dataclass

CUSTOM_KEY = "custom"


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    prompt: str


BUILTIN_STYLES: tuple[Style, ...] = (
    Style(
        key="original",
        label="Original",
        prompt="",
    ),
    Style(
        key="professional",
        label="Professionell",
        prompt=(
            "Sehr geehrte Damen und Herren, anbei finden Sie eine ausführliche, "
            "formell verfasste Stellungnahme. Die nachfolgenden Ausführungen "
            "verwenden präzise Fachsprache, korrekte Interpunktion sowie "
            "vollständige Hauptsätze in gehobenem Schriftdeutsch."
        ),
    ),
    Style(
        key="casual",
        label="Locker",
        prompt=(
            "Hey, also pass auf, ich erzähl dir mal kurz, was Sache ist. "
            "Locker rüber, ganz entspannt, so wie man halt im Alltag redet — "
            "lockere Sprache, kurze Sätze, easy zu lesen."
        ),
    ),
)


def all_styles(custom_prompt: str = "") -> list[Style]:
    styles = list(BUILTIN_STYLES)
    if custom_prompt.strip():
        styles.append(Style(key=CUSTOM_KEY, label="Eigener Stil", prompt=custom_prompt))
    return styles


def find_style(key: str, custom_prompt: str = "") -> Style:
    for s in all_styles(custom_prompt):
        if s.key == key:
            return s
    return BUILTIN_STYLES[0]
