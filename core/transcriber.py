from __future__ import annotations

from pathlib import Path

from openai import OpenAI


class Transcriber:
    def __init__(self, api_key: str, model: str, language: str = "", prompt: str = ""):
        self._api_key = api_key
        self._model = model
        self._language = language
        self._prompt = prompt
        self._client: OpenAI | None = None

    def update(self, api_key: str, model: str, language: str = "", prompt: str = "") -> None:
        if api_key != self._api_key:
            self._api_key = api_key
            self._client = None
        self._model = model
        self._language = language
        self._prompt = prompt

    def set_prompt(self, prompt: str) -> None:
        self._prompt = prompt

    def _client_or_raise(self) -> OpenAI:
        if not self._api_key:
            raise RuntimeError("OpenAI API-Key fehlt — bitte in den Einstellungen setzen.")
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def transcribe(self, wav_path: Path) -> str:
        client = self._client_or_raise()
        kwargs = {"model": self._model}
        if self._language:
            kwargs["language"] = self._language
        if self._prompt:
            kwargs["prompt"] = self._prompt
        with open(wav_path, "rb") as f:
            result = client.audio.transcriptions.create(file=f, **kwargs)
        return (result.text or "").strip()
