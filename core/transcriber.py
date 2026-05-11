from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

from openai import OpenAI

from core import local_engine
from core.config import Engine, LocalModelSize

log = logging.getLogger("typestream.transcriber")

LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
LOCAL_MODELS_DIR = LOCAL_APP_DATA / "TypeStream" / "models"


class Transcriber:
    def __init__(
        self,
        engine: Engine = "openai",
        api_key: str = "",
        model: str = "gpt-4o-mini-transcribe",
        local_model_size: LocalModelSize = "base",
        language: str = "",
        prompt: str = "",
    ):
        self._engine: Engine = engine
        self._api_key = api_key
        self._model = model
        self._local_model_size: LocalModelSize = local_model_size
        self._language = language
        self._prompt = prompt
        self._openai_client: OpenAI | None = None
        self._local_model: Any = None
        self._local_model_loaded_size: str | None = None
        self._local_load_lock = threading.Lock()

    def update(
        self,
        engine: Engine,
        api_key: str,
        model: str,
        local_model_size: LocalModelSize,
        language: str = "",
        prompt: str = "",
    ) -> None:
        if api_key != self._api_key:
            self._api_key = api_key
            self._openai_client = None
        if local_model_size != self._local_model_size:
            self._local_model_size = local_model_size
        self._engine = engine
        self._model = model
        self._language = language
        self._prompt = prompt

    def set_prompt(self, prompt: str) -> None:
        self._prompt = prompt

    def transcribe(self, wav_path: Path) -> str:
        if self._engine == "local":
            return self.transcribe_whisper(wav_path)
        return self.transcribe_openai(wav_path)

    def _openai_client_or_raise(self) -> OpenAI:
        if not self._api_key:
            raise RuntimeError("OpenAI API-Key fehlt — bitte in den Einstellungen setzen.")
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    def transcribe_openai(self, wav_path: Path) -> str:
        client = self._openai_client_or_raise()
        kwargs: dict[str, Any] = {"model": self._model}
        if self._language:
            kwargs["language"] = self._language
        if self._prompt:
            kwargs["prompt"] = self._prompt
        with open(wav_path, "rb") as f:
            result = client.audio.transcriptions.create(file=f, **kwargs)
        return (result.text or "").strip()

    def _local_model_or_load(self) -> Any:
        with self._local_load_lock:
            if (
                self._local_model is not None
                and self._local_model_loaded_size == self._local_model_size
            ):
                return self._local_model
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:
                raise local_engine.LocalEngineNotInstalled(
                    "Faster-Whisper ist nicht installiert. "
                    "Öffne die Einstellungen und klicke auf „Lokale Engine installieren“."
                ) from e
            LOCAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)
            log.info(
                "Loading faster-whisper model '%s' (download_root=%s)",
                self._local_model_size,
                LOCAL_MODELS_DIR,
            )
            cpu_threads = os.cpu_count() or 4
            log.info(
                "WhisperModel init: size=%s compute=int8 cpu_threads=%d",
                self._local_model_size,
                cpu_threads,
            )
            self._local_model = WhisperModel(
                self._local_model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=cpu_threads,
                num_workers=1,
                download_root=str(LOCAL_MODELS_DIR),
            )
            self._local_model_loaded_size = self._local_model_size
            return self._local_model

    def transcribe_whisper(self, wav_path: Path) -> str:
        model = self._local_model_or_load()
        kwargs: dict[str, Any] = {
            "vad_filter": True,
            "beam_size": 5,
            "condition_on_previous_text": False,
        }
        if self._language:
            kwargs["language"] = self._language
        if self._prompt:
            kwargs["initial_prompt"] = self._prompt
        segments, _info = model.transcribe(str(wav_path), **kwargs)
        text = " ".join(seg.text.strip() for seg in segments if seg.text)
        return text.strip()

    def transcribe_with(self, engine_id: str, wav_path: Path) -> str:
        if engine_id == "openai":
            return self.transcribe_openai(wav_path)
        if engine_id == "whisper":
            return self.transcribe_whisper(wav_path)
        raise ValueError(f"Unknown engine id: {engine_id}")

    def can_run_openai(self) -> bool:
        return bool(self._api_key)

    def can_run_local(self) -> bool:
        return local_engine.is_installed("whisper")

    def can_run(self, engine_id: str) -> bool:
        if engine_id == "openai":
            return self.can_run_openai()
        if engine_id == "whisper":
            return local_engine.is_installed("whisper")
        return False
