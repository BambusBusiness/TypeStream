from __future__ import annotations

import logging

from openai import OpenAI

log = logging.getLogger("typestream.refiner")

SYSTEM_TEMPLATE = (
    "Du bist ein Sprach-Stil-Redakteur. Formuliere den vom Nutzer "
    "gelieferten Text in den vorgegebenen Stil um, ohne Inhalt zu "
    "verändern oder hinzuzufügen. Antworte ausschließlich mit dem "
    "umformulierten Text, ohne Anführungszeichen oder Kommentare.\n\n"
    "Stil-Anweisung:\n{style}"
)


def refine_text(
    text: str,
    style_prompt: str,
    *,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> str:
    if not text.strip() or not style_prompt.strip() or not api_key:
        return text
    client = OpenAI(api_key=api_key)
    system = SYSTEM_TEMPLATE.format(style=style_prompt.strip())
    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0.4,
        )
        refined = (result.choices[0].message.content or "").strip()
        if not refined:
            log.warning("Refiner returned empty content, falling back to original.")
            return text
        return refined
    except Exception:
        log.exception("Refiner call failed — returning original text.")
        return text
