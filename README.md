# TypeStream

A fast voice-to-text dictation tool for Windows. Hold a global hotkey, speak, release — the transcribed text is typed straight into whichever application has focus.

## Features

- **System-wide hotkey** (Push-to-Talk or Toggle), works in any window
- **Two transcription engines:** OpenAI Cloud (fast, paid) or Faster-Whisper (local, free, offline)
- **Style transformation** (Original, Professional, Casual, or a custom prompt) via Whisper hint or LLM refinement
- **Tray-resident** — runs in the background, no taskbar clutter
- **Update notifications** through GitHub Releases
- **No telemetry**, no cloud sync — history stays local

## Install

Grab the latest installer from the [Releases page](https://github.com/BambusBusiness/TypeStream/releases/latest) and run `TypeStream-Setup-<version>.exe`.

## Quick start

1. Launch TypeStream — the tray icon appears next to the system clock.
2. On first launch the settings window opens. Pick an engine:
   - **OpenAI:** paste your API key from [platform.openai.com](https://platform.openai.com).
   - **Faster-Whisper:** click *Install* to fetch the local model (~150 MB).
3. Place your cursor in any text field, hold **F9**, speak, and release. The text appears at the cursor.

## Build from source

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.\build.bat
```

The build produces a portable bundle at `dist\TypeStream\TypeStream.exe`. With Inno Setup 6 installed, it additionally produces a Windows installer at `dist\installer\TypeStream-Setup-<version>.exe`.
