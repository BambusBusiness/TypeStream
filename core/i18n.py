"""Lightweight runtime localization for TypeStream.

Design notes
------------

The app started life with all strings inlined in German. We don't want to
move to Qt's lupdate/.ts/.qm pipeline (extra build step, extra tooling
that the rest of the project doesn't use) so this is a plain Python
dictionary lookup with a binding helper for live language switching.

The binding pattern is the load-bearing trick. Every place that calls
`i18n.bind(setter, key, **fmt)` does two things:

1. Calls `setter(t(key, **fmt))` once, right now, so the widget shows the
   current translation immediately.
2. Remembers the setter + key + format args so that on `set_language(...)`
   the binding gets re-applied with the new translation.

Setters are weakly held via the *bound method* of the widget — when the
widget is destroyed, the next attempt to call the setter raises
`RuntimeError("wrapped C/C++ object ... has been deleted")` and we drop
the binding silently. No explicit unbind in widget destructors needed.

Strings that should NOT be translated:

- Log messages (`log.info(...)` etc.) — English only, internal-facing.
- File paths, env var names, version strings — language-agnostic.
- Vendor / proper names (OpenAI, Faster-Whisper, GPT-4o, etc.).
"""
from __future__ import annotations

import logging
import locale
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger("typestream.i18n")

# Codes we actually ship translations for. "system" in Config means
# "follow the OS locale at startup"; once `_active` is set it's always
# one of the concrete codes below.
SUPPORTED_LANGS = ("de", "en")
DEFAULT_LANG = "de"


def _detect_system_lang() -> str:
    try:
        code, _ = locale.getlocale()
        if code:
            short = code.split("_", 1)[0].lower()
            if short in SUPPORTED_LANGS:
                return short
    except Exception:
        log.debug("locale.getlocale() failed", exc_info=True)
    return DEFAULT_LANG


# Translation table. Keys are dotted paths grouped by area; values map
# language code to translated string. Use `{var}`-style placeholders for
# interpolation — `t()` passes **kwargs straight to .format(). If a key
# is missing for the requested language the key itself is returned (so
# missing translations are immediately visible during development).
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- App title / generic ---
    "app.title": {
        "de": "TypeStream",
        "en": "TypeStream",
    },
    "app.tray.tooltip_idle": {
        "de": "TypeStream — bereit",
        "en": "TypeStream — ready",
    },
    "app.tray.tooltip_recording": {
        "de": "TypeStream — Aufnahme läuft",
        "en": "TypeStream — recording",
    },
    "app.tray.tooltip_busy": {
        "de": "TypeStream — Transkription läuft",
        "en": "TypeStream — transcribing",
    },

    # --- Tray menu ---
    "tray.menu.open_history": {
        "de": "Verlauf öffnen",
        "en": "Open history",
    },
    "tray.menu.settings": {
        "de": "Einstellungen",
        "en": "Settings",
    },
    "tray.menu.copy_last": {
        "de": "Letzte Aufnahme kopieren",
        "en": "Copy last transcription",
    },
    "tray.menu.quit": {
        "de": "Beenden",
        "en": "Quit",
    },
    "tray.menu.style": {
        "de": "Stil",
        "en": "Style",
    },
    "tray.menu.update_install": {
        "de": "Update v{version} installieren",
        "en": "Install update v{version}",
    },

    # --- Main window: history page ---
    "history.stats_line": {
        "de": "{today} Wörter heute  ·  {total} Wörter gesamt",
        "en": "{today} words today  ·  {total} words total",
    },
    "history.empty": {
        "de": "Noch keine Transkriptionen.\nHalte deinen Aufnahme-Hotkey, sprich kurz, lass los — der Text erscheint hier.",
        "en": "No transcriptions yet.\nHold your recording hotkey, speak briefly, release — the text shows up here.",
    },
    "history.action.copy": {
        "de": "Kopieren",
        "en": "Copy",
    },
    "history.action.insert": {
        "de": "Einfügen",
        "en": "Paste",
    },
    "history.action.delete": {
        "de": "Löschen",
        "en": "Delete",
    },
    "history.action.clear_all": {
        "de": "Alle löschen",
        "en": "Delete all",
    },
    "history.header.style": {
        "de": "STIL",
        "en": "STYLE",
    },
    "history.header.settings": {
        "de": "Einstellungen",
        "en": "Settings",
    },

    # --- Update banner ---
    "banner.update_ready": {
        "de": "Update auf v{version} bereit — wird mit einem Klick still installiert.",
        "en": "Update to v{version} ready — installs silently with one click.",
    },
    "banner.install_now": {
        "de": "Jetzt installieren",
        "en": "Install now",
    },
    "banner.dismiss_tooltip": {
        "de": "Banner für diese Sitzung ausblenden",
        "en": "Hide banner for this session",
    },

    # --- Settings: navigation ---
    "settings.nav.transcription": {
        "de": "Transkription",
        "en": "Transcription",
    },
    "settings.nav.hotkeys": {
        "de": "Hotkeys",
        "en": "Hotkeys",
    },
    "settings.nav.recording": {
        "de": "Aufnahme",
        "en": "Recording",
    },
    "settings.nav.style": {
        "de": "Stil",
        "en": "Style",
    },
    "settings.nav.display": {
        "de": "Anzeige",
        "en": "Display",
    },
    "settings.nav.stats": {
        "de": "Statistik",
        "en": "Statistics",
    },
    "settings.nav.updates": {
        "de": "Updates",
        "en": "Updates",
    },

    # --- Settings header ---
    "settings.title": {
        "de": "Einstellungen",
        "en": "Settings",
    },
    "settings.back": {
        "de": "← Verlauf",
        "en": "← History",
    },

    # --- Settings: transcription page ---
    "settings.transcription.engine": {
        "de": "Quelle",
        "en": "Engine",
    },
    "settings.transcription.engine_cloud": {
        "de": "OpenAI API (Cloud)",
        "en": "OpenAI API (cloud)",
    },
    "settings.transcription.engine_local": {
        "de": "Faster-Whisper (Lokal)",
        "en": "Faster-Whisper (local)",
    },
    "settings.transcription.engine_help": {
        "de": "Wer dein Audio in Text umwandelt.\nOpenAI = schnelle Cloud (~0,2 Cent pro Minute Audio).\nFaster-Whisper = läuft lokal auf deinem Rechner — kostenlos und privat, einmaliger Modell-Download nötig.",
        "en": "Who turns your audio into text.\nOpenAI = fast cloud (~$0.003 per audio minute).\nFaster-Whisper = runs locally on your machine — free and private, one-off model download required.",
    },
    "settings.transcription.api_key": {
        "de": "API-Key",
        "en": "API key",
    },
    "settings.transcription.api_key_placeholder": {
        "de": "sk-...",
        "en": "sk-...",
    },
    "settings.transcription.api_key_help": {
        "de": "Dein persönlicher Schlüssel von platform.openai.com (beginnt mit sk-...).\nWird nur lokal in deiner Config-Datei gespeichert.",
        "en": "Your personal key from platform.openai.com (starts with sk-...).\nStored locally in your config file only.",
    },
    "settings.transcription.model": {
        "de": "Modell",
        "en": "Model",
    },
    "settings.transcription.model_help": {
        "de": "Welches OpenAI-Transkriptions-Modell genutzt wird.\nmini-transcribe = günstig und sehr gut (Voreinstellung).\ngpt-4o-transcribe = beste Qualität, doppelt so teuer.",
        "en": "Which OpenAI transcription model to use.\nmini-transcribe = cheap and very good (default).\ngpt-4o-transcribe = best quality, twice the price.",
    },
    "settings.transcription.local_size": {
        "de": "Modell-Größe",
        "en": "Model size",
    },
    "settings.transcription.local_size_help": {
        "de": "Größere Modelle erkennen genauer, brauchen aber mehr Festplattenplatz und RAM.\nbase ist ein guter Mittelweg für die meisten Rechner.",
        "en": "Larger models recognize more accurately but need more disk space and RAM.\nbase is a good compromise for most machines.",
    },
    "settings.transcription.language": {
        "de": "Sprache",
        "en": "Language",
    },
    "settings.transcription.language_help": {
        "de": "Hilft der Erkennung, wenn du immer in einer Sprache diktierst.\nAuto-Erkennung klappt meist gut, kann aber bei sehr kurzen Aufnahmen daneben liegen.",
        "en": "Helps recognition if you always dictate in one language.\nAuto-detect usually works but can miss on very short recordings.",
    },
    "settings.transcription.language_auto": {
        "de": "Auto-Erkennung",
        "en": "Auto-detect",
    },
    "settings.transcription.local_hint": {
        "de": "Lokale Modelle werden in dein Benutzerverzeichnis geladen (AppData/Local/TypeStream/models). Keine Daten verlassen deinen Rechner.",
        "en": "Local models are downloaded into your user folder (AppData/Local/TypeStream/models). No data leaves your machine.",
    },
    "settings.transcription.install_btn": {
        "de": "Lokale Engine installieren",
        "en": "Install local engine",
    },
    "settings.transcription.install_btn_whisper": {
        "de": "Faster-Whisper installieren",
        "en": "Install Faster-Whisper",
    },
    "settings.transcription.install_missing": {
        "de": "Faster-Whisper ist auf diesem Rechner noch nicht installiert.",
        "en": "Faster-Whisper is not installed on this machine yet.",
    },
    "settings.transcription.benchmark": {
        "de": "Benchmark-Modus (beide Engines vergleichen)",
        "en": "Benchmark mode (compare both engines)",
    },
    "settings.transcription.benchmark_help": {
        "de": "Schickt jede Aufnahme parallel an beide Engines, damit du die Geschwindigkeit vergleichen kannst (siehe Statistik-Tab).\nKostet etwas mehr und braucht beide Engines konfiguriert.",
        "en": "Sends every recording to both engines in parallel so you can compare speed (see Statistics tab).\nCosts a bit more and needs both engines configured.",
    },
    "settings.transcription.benchmark_hint": {
        "de": "Jede Aufnahme wird gleichzeitig durch OpenAI und Faster-Whisper geschickt. Beide Laufzeiten landen unter „Statistik\". Die Einfügung kommt aus der oben gewählten Quelle.",
        "en": "Each recording is sent through OpenAI and Faster-Whisper in parallel. Both run-times show up under \"Statistics\". The pasted text comes from the engine you chose above.",
    },

    # Compound combo labels — keep the model/size identifier verbatim,
    # translate only the descriptive tail.
    "settings.transcription.model_mini": {
        "de": "gpt-4o-mini-transcribe  ·  ~$0.003/min",
        "en": "gpt-4o-mini-transcribe  ·  ~$0.003/min",
    },
    "settings.transcription.model_whisper": {
        "de": "whisper-1  ·  ~$0.006/min",
        "en": "whisper-1  ·  ~$0.006/min",
    },
    "settings.transcription.model_4o": {
        "de": "gpt-4o-transcribe  ·  ~$0.006/min  ·  beste Qualität",
        "en": "gpt-4o-transcribe  ·  ~$0.006/min  ·  best quality",
    },
    "settings.transcription.local_tiny": {
        "de": "tiny  ·  ~75 MB  ·  schnellste",
        "en": "tiny  ·  ~75 MB  ·  fastest",
    },
    "settings.transcription.local_base": {
        "de": "base  ·  ~150 MB  ·  empfohlen",
        "en": "base  ·  ~150 MB  ·  recommended",
    },
    "settings.transcription.local_small": {
        "de": "small  ·  ~470 MB  ·  beste Qualität",
        "en": "small  ·  ~470 MB  ·  best quality",
    },
    "settings.style.refine_mini": {
        "de": "gpt-4o-mini  ·  günstig, schnell",
        "en": "gpt-4o-mini  ·  cheap, fast",
    },
    "settings.style.refine_4o": {
        "de": "gpt-4o  ·  beste Qualität",
        "en": "gpt-4o  ·  best quality",
    },
    "settings.stats.bench_openai": {
        "de": "OpenAI (Cloud)",
        "en": "OpenAI (cloud)",
    },
    "settings.stats.bench_whisper": {
        "de": "Faster-Whisper (Lokal)",
        "en": "Faster-Whisper (local)",
    },

    # Whisper input language combo (Sprache der Eingabe, nicht UI-Sprache).
    "lang.auto": {"de": "Auto-Erkennung", "en": "Auto-detect"},
    "lang.de":   {"de": "Deutsch",        "en": "German"},
    "lang.en":   {"de": "Englisch",       "en": "English"},
    "lang.fr":   {"de": "Französisch",    "en": "French"},
    "lang.es":   {"de": "Spanisch",       "en": "Spanish"},
    "lang.it":   {"de": "Italienisch",    "en": "Italian"},
    "lang.nl":   {"de": "Niederländisch", "en": "Dutch"},
    "lang.pt":   {"de": "Portugiesisch",  "en": "Portuguese"},
    "lang.pl":   {"de": "Polnisch",       "en": "Polish"},
    "lang.ja":   {"de": "Japanisch",      "en": "Japanese"},
    "lang.zh":   {"de": "Chinesisch",     "en": "Chinese"},

    # --- Local engine install dialog ---
    "install_dialog.title": {
        "de": "{engine} installieren",
        "en": "Install {engine}",
    },
    "install_dialog.intro_suffix": {
        "de": "Die Installation läuft in dein Benutzerverzeichnis — keine Daten verlassen deinen Rechner. Das kann mehrere Minuten dauern.",
        "en": "The install lands in your user folder — no data leaves your machine. This can take a few minutes.",
    },
    "install_dialog.status_ready": {
        "de": "Bereit zur Installation.",
        "en": "Ready to install.",
    },
    "install_dialog.status_running": {
        "de": "Starte Installation …",
        "en": "Starting install …",
    },
    "install_dialog.status_done": {
        "de": "Installation abgeschlossen.",
        "en": "Install completed.",
    },
    "install_dialog.status_failed": {
        "de": "Installation fehlgeschlagen.",
        "en": "Install failed.",
    },
    "install_dialog.log_placeholder": {
        "de": "pip-Output erscheint hier während der Installation …",
        "en": "pip output appears here during the install …",
    },
    "install_dialog.btn_install": {
        "de": "Installieren",
        "en": "Install",
    },
    "install_dialog.btn_close": {
        "de": "Schließen",
        "en": "Close",
    },
    "install_dialog.btn_retry": {
        "de": "Erneut versuchen",
        "en": "Try again",
    },
    "install_dialog.error_prefix": {
        "de": "FEHLER: {error}",
        "en": "ERROR: {error}",
    },

    # --- Settings: hotkeys page ---
    "settings.hotkeys.record": {
        "de": "Aufnahme",
        "en": "Record",
    },
    "settings.hotkeys.record_help": {
        "de": "Welche Taste du drückst, um zu diktieren (z. B. F9).\nKlick auf den Button und drück dann die gewünschte Taste oder Maustaste.",
        "en": "Which key you press to dictate (e.g. F9).\nClick the button and then press the key or mouse button you want.",
    },
    "settings.hotkeys.mode": {
        "de": "Modus",
        "en": "Mode",
    },
    "settings.hotkeys.mode_ptt": {
        "de": "Push-to-Talk (Taste halten)",
        "en": "Push-to-Talk (hold key)",
    },
    "settings.hotkeys.mode_toggle": {
        "de": "Toggle (Drücken: Start, nochmal: Stop)",
        "en": "Toggle (press: start, press again: stop)",
    },
    "settings.hotkeys.mode_help": {
        "de": "Push-to-Talk = Taste halten, beim Loslassen wird transkribiert.\nToggle = einmal drücken zum Starten, nochmal zum Stoppen.",
        "en": "Push-to-Talk = hold the key, transcription starts when you release.\nToggle = press once to start, press again to stop.",
    },
    "settings.hotkeys.paste": {
        "de": "Letzten Text einfügen",
        "en": "Paste last text",
    },
    "settings.hotkeys.paste_help": {
        "de": "Fügt den zuletzt erkannten Text noch einmal ein — nützlich, wenn das Auto-Einfügen mal nicht klappt.\nHier sind Tastenkombinationen erlaubt (z. B. Strg+Alt+V).",
        "en": "Re-pastes the last transcribed text — useful when auto-paste doesn't work.\nKey combinations are allowed here (e.g. Ctrl+Alt+V).",
    },
    "settings.hotkeys.hint": {
        "de": "Klicke auf einen Button und drücke dann die gewünschte Taste oder Maustaste. Push-to-Talk benötigt eine einzelne Taste.",
        "en": "Click a button and then press the key or mouse button you want. Push-to-Talk needs a single key.",
    },

    # --- Settings: recording page ---
    "settings.recording.microphone": {
        "de": "Mikrofon",
        "en": "Microphone",
    },
    "settings.recording.system_default": {
        "de": "Systemstandard",
        "en": "System default",
    },
    "settings.recording.unavailable_suffix": {
        "de": "  ·  nicht verfügbar",
        "en": "  ·  unavailable",
    },
    "settings.recording.min_duration": {
        "de": "Min. Aufnahme-Dauer",
        "en": "Min. recording duration",
    },
    "settings.recording.history_limit": {
        "de": "Verlauf-Limit",
        "en": "History limit",
    },
    "settings.recording.play_sounds": {
        "de": "Akustisches Feedback (Start- / Stop-Ton)",
        "en": "Audio feedback (start / stop beep)",
    },
    "settings.recording.beep_volume": {
        "de": "Aufnahme-Ton",
        "en": "Recording beep",
    },
    "settings.recording.warning_volume": {
        "de": "Warnton",
        "en": "Warning chime",
    },
    "settings.recording.show_overlay": {
        "de": "Visuelles Overlay während Aufnahme",
        "en": "Visual overlay during recording",
    },
    "settings.recording.autostart": {
        "de": "Bei Windows-Start automatisch starten",
        "en": "Start automatically with Windows",
    },

    # --- Settings: style page ---
    "settings.style.active": {
        "de": "Aktiver Stil",
        "en": "Active style",
    },
    "settings.style.active_help": {
        "de": "Wie der erkannte Text formatiert wird.\nOriginal = unverändert. Professionell = formell. Locker = umgangssprachlich.\nEigener Stil erscheint, sobald du unten einen Beispieltext einträgst.",
        "en": "How the transcribed text is formatted.\nOriginal = unchanged. Professional = formal. Casual = colloquial.\nCustom style appears once you enter an example text below.",
    },
    "settings.style.mode": {
        "de": "Stil-Modus",
        "en": "Style mode",
    },
    "settings.style.mode_hint": {
        "de": "Whisper-Hint  ·  schnell, kostenlos",
        "en": "Whisper hint  ·  fast, free",
    },
    "settings.style.mode_refine": {
        "de": "LLM-Refine  ·  extra GPT-Aufruf, teurer",
        "en": "LLM refine  ·  extra GPT call, more expensive",
    },
    "settings.style.mode_help": {
        "de": "Whisper-Hint = günstig: der Stil-Beispieltext wird Whisper als Vorlage mitgegeben (subtiler Effekt).\nLLM-Refine = klare Wirkung: der fertige Text wird zusätzlich von GPT umformuliert. Kostet einen weiteren API-Aufruf pro Aufnahme.",
        "en": "Whisper hint = cheap: the style sample is passed to Whisper as a prompt (subtle effect).\nLLM refine = clear effect: the finished text is additionally rephrased by GPT. Costs one extra API call per recording.",
    },
    "settings.style.refine_model": {
        "de": "Refine-Modell",
        "en": "Refine model",
    },
    "settings.style.refine_model_help": {
        "de": "Welches GPT-Modell den Text umformuliert.\nmini = günstig und schnell, gpt-4o = genauer aber teurer.",
        "en": "Which GPT model rephrases the text.\nmini = cheap and fast, gpt-4o = more accurate but pricier.",
    },
    "settings.style.custom": {
        "de": "Eigener Stil",
        "en": "Custom style",
    },
    "settings.style.custom_placeholder": {
        "de": "Optionaler eigener Stil-Prompt — z. B. ein Beispieltext im gewünschten Stil. Leer lassen, um nur die vordefinierten Stile zu nutzen.",
        "en": "Optional custom style prompt — e.g. an example text in the desired style. Leave empty to use only the built-in styles.",
    },
    "settings.style.custom_help": {
        "de": "Schreib hier einen Absatz so, wie deine Ausgabe klingen soll.\nSobald das Feld ausgefüllt ist, taucht 'Eigener Stil' im Dropdown oben auf.",
        "en": "Write a paragraph the way you want your output to sound.\nOnce the field has text, 'Custom style' appears in the dropdown above.",
    },
    "settings.style.hint_body": {
        "de": "Whisper-Hint: günstig, der Stil-Beispieltext wird als Prompt an Whisper geschickt — der Effekt ist subtil.\nLLM-Refine: das fertige Transkript wird zusätzlich an GPT geschickt und konsequent umformuliert — kostet einen weiteren API-Aufruf pro Aufnahme.\n\nDen aktiven Stil kannst du auch hier, oben im Hauptfenster oder im Tray-Menü wechseln. Ein leerer Custom-Prompt blendet den Eintrag „Eigener Stil\" aus.",
        "en": "Whisper hint: cheap, the style sample is sent as a prompt to Whisper — effect is subtle.\nLLM refine: the finished transcript is additionally sent to GPT and rephrased consistently — costs one extra API call per recording.\n\nYou can switch the active style here, at the top of the main window, or in the tray menu. An empty custom prompt hides the \"Custom style\" entry.",
    },

    # --- Settings: display (appearance) page ---
    "settings.display.theme": {
        "de": "Theme",
        "en": "Theme",
    },
    "settings.display.theme_system": {
        "de": "System (automatisch)",
        "en": "System (automatic)",
    },
    "settings.display.theme_dark": {
        "de": "Dunkel",
        "en": "Dark",
    },
    "settings.display.theme_light": {
        "de": "Hell",
        "en": "Light",
    },
    "settings.display.theme_help": {
        "de": "Hell oder Dunkel.\nSystem folgt dem Windows-Hell/Dunkel-Modus automatisch.",
        "en": "Light or dark.\nSystem follows Windows' light/dark setting automatically.",
    },
    "settings.display.ui_language": {
        "de": "Anzeigesprache",
        "en": "Display language",
    },
    "settings.display.ui_language_system": {
        "de": "System (automatisch)",
        "en": "System (automatic)",
    },
    "settings.display.ui_language_help": {
        "de": "Sprache der App-Oberfläche.\nÄnderungen greifen sofort, ohne Neustart.",
        "en": "Language of the app interface.\nChanges take effect immediately, no restart needed.",
    },

    # --- Settings: stats page ---
    "settings.stats.intro": {
        "de": "Durchschnittliche Transkriptions-Latenz der letzten 10 Aufnahmen für das gewählte Engine-Paar.",
        "en": "Average transcription latency over the last 10 recordings for the selected engine pair.",
    },
    "settings.stats.engine_a": {
        "de": "Engine A",
        "en": "Engine A",
    },
    "settings.stats.engine_a_help": {
        "de": "Erste Engine im Vergleich.\nSinnvoll nur, wenn der Benchmark-Modus (im Transkriptions-Tab) aktiv ist — sonst werden nur Daten für die aktive Engine gesammelt.",
        "en": "First engine in the comparison.\nOnly useful when benchmark mode (on the Transcription tab) is on — otherwise we only collect data for the active engine.",
    },
    "settings.stats.engine_b": {
        "de": "Engine B",
        "en": "Engine B",
    },
    "settings.stats.engine_b_help": {
        "de": "Zweite Engine im Vergleich.\nWähle eine andere als bei Engine A, damit ein sinnvoller Vergleich entsteht.",
        "en": "Second engine in the comparison.\nPick a different one than Engine A so the comparison is meaningful.",
    },
    "settings.stats.no_data": {
        "de": "noch keine Daten",
        "en": "no data yet",
    },
    "settings.stats.avg": {
        "de": "Ø {seconds:.2f} s",
        "en": "avg {seconds:.2f} s",
    },
    "settings.stats.count": {
        "de": "n = {count}",
        "en": "n = {count}",
    },
    "settings.stats.verdict_faster_a": {
        "de": "{a} ist im Mittel {ratio:.1f}× schneller als {b}.",
        "en": "{a} is on average {ratio:.1f}x faster than {b}.",
    },
    "settings.stats.verdict_faster_b": {
        "de": "{b} ist im Mittel {ratio:.1f}× schneller als {a}.",
        "en": "{b} is on average {ratio:.1f}x faster than {a}.",
    },
    "settings.stats.verdict_equal": {
        "de": "Beide Engines sind gleich schnell.",
        "en": "Both engines run at the same speed.",
    },
    "settings.stats.verdict_same_pair": {
        "de": "Wähle zwei verschiedene Engines, um sie zu vergleichen.",
        "en": "Pick two different engines to compare them.",
    },
    "settings.stats.verdict_benchmark_off": {
        "de": "Aktiviere den Benchmark-Modus, um beide Engines zu vergleichen.",
        "en": "Turn on benchmark mode to compare both engines.",
    },

    # --- Settings: updates page ---
    "settings.updates.intro": {
        "de": "TypeStream prüft beim Start auf neue Versionen, lädt den Installer im Hintergrund und blendet im Hauptfenster einen „Jetzt installieren\"-Knopf ein. Falls ein Update etwas kaputt macht, kannst du hier mit einem Klick auf die vorherige Version zurück.",
        "en": "TypeStream checks for new releases on launch, downloads the installer in the background, and surfaces an \"Install now\" button in the main window. If an update breaks something, one click here rolls back to the previous version.",
    },
    "settings.updates.current_section": {
        "de": "AKTUELLE VERSION",
        "en": "CURRENT VERSION",
    },
    "settings.updates.pending_section": {
        "de": "VERFÜGBARES UPDATE",
        "en": "AVAILABLE UPDATE",
    },
    "settings.updates.rollback_section": {
        "de": "ROLLBACK",
        "en": "ROLLBACK",
    },
    "settings.updates.check_btn_idle": {
        "de": "Jetzt nach Updates suchen",
        "en": "Check for updates now",
    },
    "settings.updates.check_btn_running": {
        "de": "Suche läuft …",
        "en": "Checking …",
    },
    "settings.updates.check_btn_up_to_date": {
        "de": "Du bist auf der aktuellsten Version ✓",
        "en": "You're on the latest version ✓",
    },
    "settings.updates.no_update": {
        "de": "Kein Update verfügbar.",
        "en": "No update available.",
    },
    "settings.updates.pending_ready": {
        "de": "v{version} ist heruntergeladen und bereit zum Installieren.",
        "en": "v{version} is downloaded and ready to install.",
    },
    "settings.updates.pending_notes": {
        "de": "Release-Notes: {notes}",
        "en": "Release notes: {notes}",
    },
    "settings.updates.rollback_no_history": {
        "de": "Noch keine vorherige Version aufgezeichnet — der Rollback steht nach dem ersten Update zur Verfügung.",
        "en": "No previous version recorded yet — rollback is available after the first update.",
    },
    "settings.updates.rollback_only_installed": {
        "de": "Vorherige Version: v{version}. Rollback nur aus der installierten App heraus (nicht aus dem Dev-Checkout).",
        "en": "Previous version: v{version}. Rollback only works from the installed app, not from a dev checkout.",
    },
    "settings.updates.rollback_description": {
        "de": "Vor dem letzten Update lief TypeStream auf Version v{version}. Klick installiert diese Version still aus dem GitHub-Release und startet die App neu.",
        "en": "Before the last update TypeStream was on v{version}. Clicking installs that version silently from the GitHub release and restarts the app.",
    },
    "settings.updates.rollback_btn_default": {
        "de": "Auf vorherige Version zurück",
        "en": "Roll back to previous version",
    },
    "settings.updates.rollback_btn_target": {
        "de": "Auf v{version} zurück",
        "en": "Roll back to v{version}",
    },
    "settings.updates.rollback_btn_loading": {
        "de": "Lade v{version} …",
        "en": "Downloading v{version} …",
    },

    # --- Hotkey capture button ---
    "hotkey.capture.placeholder": {
        "de": "(kein Hotkey)",
        "en": "(no hotkey)",
    },
    "hotkey.capture.prompt": {
        "de": "Drücke jetzt eine Taste oder Maustaste …  (Esc = Abbrechen)",
        "en": "Press a key or mouse button now …  (Esc to cancel)",
    },
    "hotkey.capture.mouse_left": {
        "de": "Maus Links",
        "en": "Left mouse",
    },
    "hotkey.capture.mouse_right": {
        "de": "Maus Rechts",
        "en": "Right mouse",
    },
    "hotkey.capture.mouse_middle": {
        "de": "Maus Mitte",
        "en": "Middle mouse",
    },
    "hotkey.capture.mouse_x1": {
        "de": "Maustaste 4 (X1)",
        "en": "Mouse button 4 (X1)",
    },
    "hotkey.capture.mouse_x2": {
        "de": "Maustaste 5 (X2)",
        "en": "Mouse button 5 (X2)",
    },

    # --- Runtime notifications ---
    "notify.api_key_missing": {
        "de": "Kein API-Key gesetzt — bitte Einstellungen öffnen.",
        "en": "No API key set — open Settings.",
    },
    "notify.local_not_installed": {
        "de": "Faster-Whisper ist nicht installiert — bitte Einstellungen öffnen.",
        "en": "Faster-Whisper is not installed — open Settings.",
    },
    "notify.record_start_failed": {
        "de": "Aufnahme-Start fehlgeschlagen: {error}",
        "en": "Failed to start recording: {error}",
    },
    "notify.record_stop_failed": {
        "de": "Aufnahme-Stop fehlgeschlagen: {error}",
        "en": "Failed to stop recording: {error}",
    },
    "notify.record_too_short": {
        "de": "Aufnahme zu kurz (< {min:.1f}s)",
        "en": "Recording too short (< {min:.1f}s)",
    },
    "notify.no_speech": {
        "de": "Keine Sprache erkannt",
        "en": "No speech detected",
    },
    "notify.transcription_failed": {
        "de": "Transkription fehlgeschlagen: {error}",
        "en": "Transcription failed: {error}",
    },
    "notify.paste_failed": {
        "de": "Auto-Einfügen fehlgeschlagen — Text in Zwischenablage. Strg+V einfügen.",
        "en": "Auto-paste failed — text is on the clipboard. Press Ctrl+V to insert.",
    },
    "notify.history_empty": {
        "de": "Kein Text im Verlauf.",
        "en": "No text in the history.",
    },
    "notify.copied_last": {
        "de": "Letzter Text in Zwischenablage kopiert.",
        "en": "Last text copied to clipboard.",
    },
    "notify.copied": {
        "de": "In Zwischenablage kopiert.",
        "en": "Copied to clipboard.",
    },
    "notify.style_changed": {
        "de": "Stil: {label}",
        "en": "Style: {label}",
    },
    "notify.hotkey_error": {
        "de": "Hotkey-Fehler: {error}",
        "en": "Hotkey error: {error}",
    },
    "notify.ptt_as_toggle": {
        "de": "Tastenkombination erkannt — PTT wird als Toggle behandelt.",
        "en": "Key combination detected — PTT is being treated as toggle.",
    },
    "notify.update_available_tray": {
        "de": "Update verfügbar: v{version} — siehe Tray-Menü.",
        "en": "Update available: v{version} — see tray menu.",
    },
    "notify.update_ready_banner": {
        "de": "Update v{version} ist bereit — im Hauptfenster auf 'Jetzt installieren' klicken.",
        "en": "Update v{version} is ready — click 'Install now' in the main window.",
    },
    "notify.update_download_failed_short": {
        "de": "Update v{version} verfügbar — Download fehlgeschlagen, Details in Settings → Updates.",
        "en": "Update v{version} available — download failed, see Settings → Updates for details.",
    },
    "notify.update_download_failed_long": {
        "de": "Auto-Download von v{version} fehlgeschlagen (meist eine Antivirus-Sperre oder ein File-Lock im %APPDATA%\\TypeStream\\updates-Ordner). Tray-Menü → „Update v{version} installieren\" öffnet das Release im Browser. Details siehe typestream.log.",
        "en": "Auto-download of v{version} failed (usually an antivirus block or a file lock in the %APPDATA%\\TypeStream\\updates folder). Tray menu → \"Install update v{version}\" opens the release in the browser. Details in typestream.log.",
    },
    "notify.update_installer_failed": {
        "de": "Update-Installer konnte nicht gestartet werden — bitte manuell ausführen: {path}",
        "en": "Update installer could not be launched — run it manually: {path}",
    },
    "notify.update_browser_failed": {
        "de": "Konnte Browser nicht öffnen. URL: {url}",
        "en": "Failed to open the browser. URL: {url}",
    },
    "notify.up_to_date": {
        "de": "Du bist auf der aktuellsten Version.",
        "en": "You're on the latest version.",
    },
    "notify.rollback_running": {
        "de": "Rollback läuft bereits …",
        "en": "Rollback already running …",
    },
    "notify.rollback_no_previous": {
        "de": "Keine vorherige Version bekannt.",
        "en": "No previous version recorded.",
    },
    "notify.rollback_dev_checkout": {
        "de": "Rollback geht nur aus der installierten App heraus — aus dem Dev-Checkout heraus nicht möglich.",
        "en": "Rollback only works from the installed app, not from a dev checkout.",
    },
    "notify.rollback_failed_no_release": {
        "de": "Rollback auf v{version} fehlgeschlagen: Release v{version} ist auf GitHub nicht (mehr) verfügbar oder hat keinen Installer angehängt.",
        "en": "Rollback to v{version} failed: release v{version} is no longer available on GitHub or has no installer attached.",
    },
    "notify.rollback_failed_local": {
        "de": "Rollback auf v{version} fehlgeschlagen: Download oder Datei-Umbenennung im %APPDATA%\\TypeStream\\updates-Ordner ist fehlgeschlagen. Details siehe typestream.log.",
        "en": "Rollback to v{version} failed: download or file rename in %APPDATA%\\TypeStream\\updates failed. See typestream.log for details.",
    },
}


class _I18n(QObject):
    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Concrete language code (always one of SUPPORTED_LANGS). The
        # config-level "system" is resolved at apply_language() time.
        self._active = DEFAULT_LANG
        self._bindings: list[tuple[Callable[[str], None], str, dict]] = []

    def current(self) -> str:
        return self._active

    def apply_language(self, code: str) -> None:
        """Set the active language. Accepts a concrete code ("de", "en")
        or "system" which is resolved against the OS locale."""
        if code == "system":
            resolved = _detect_system_lang()
        else:
            resolved = code if code in SUPPORTED_LANGS else DEFAULT_LANG
        if resolved == self._active:
            return
        log.info("UI language: %s -> %s", self._active, resolved)
        self._active = resolved
        self._apply_all_bindings()
        self.language_changed.emit()

    def t(self, key: str, **kwargs) -> str:
        entry = _TRANSLATIONS.get(key)
        if entry is None:
            log.debug("missing translation key: %s", key)
            return key
        text = entry.get(self._active) or entry.get(DEFAULT_LANG) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                log.debug("format failed for %s with %r", key, kwargs, exc_info=True)
                return text
        return text

    def bind(self, setter: Callable[[str], None], key: str, **kwargs) -> None:
        """Register `setter(t(key, **kwargs))` to be called now and on
        every future language change. `setter` is typically a bound
        method like `label.setText` or `button.setToolTip`."""
        self._bindings.append((setter, key, dict(kwargs)))
        try:
            setter(self.t(key, **kwargs))
        except RuntimeError:
            # Widget already gone — drop the binding immediately.
            self._bindings.pop()

    def _apply_all_bindings(self) -> None:
        alive: list[tuple[Callable[[str], None], str, dict]] = []
        for setter, key, kwargs in self._bindings:
            try:
                setter(self.t(key, **kwargs))
                alive.append((setter, key, kwargs))
            except RuntimeError:
                # Widget was destroyed; drop the binding.
                continue
        self._bindings = alive


# Module-level singleton. Imported as `from core.i18n import i18n`.
i18n = _I18n()


def t(key: str, **kwargs) -> str:
    """Convenience shortcut for one-off lookups that don't need a binding."""
    return i18n.t(key, **kwargs)
