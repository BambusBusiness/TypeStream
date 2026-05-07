from __future__ import annotations

import logging
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

log = logging.getLogger("typestream.recorder")

SAMPLE_RATE = 16000
CHANNELS = 1


class AudioRecorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._capturing = False

    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks = []
            self._capturing = True
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                latency="low",
                callback=self._on_audio,
            )
            stream.start()
        except Exception:
            with self._lock:
                self._capturing = False
            raise
        self._stream = stream

    def stop(self, min_duration_s: float = 0.0) -> Path | None:
        if self._stream is None:
            return None
        stream = self._stream
        self._stream = None
        with self._lock:
            self._capturing = False
            chunks = self._chunks
            self._chunks = []
        threading.Thread(
            target=self._close_stream,
            args=(stream,),
            name="recorder-close",
            daemon=True,
        ).start()
        if not chunks:
            return None
        audio = np.concatenate(chunks, axis=0)
        if audio.size == 0:
            return None
        duration = audio.shape[0] / SAMPLE_RATE
        if duration < min_duration_s:
            return None
        out = Path(tempfile.gettempdir()) / f"typestream_{int(time.time() * 1000)}.wav"
        sf.write(str(out), audio, SAMPLE_RATE, subtype="PCM_16")
        return out

    def _on_audio(self, indata, frames, time_info, status) -> None:
        with self._lock:
            if not self._capturing:
                return
            self._chunks.append(indata.copy())

    @staticmethod
    def _close_stream(stream: sd.InputStream) -> None:
        try:
            stream.stop()
            stream.close()
        except Exception:
            log.exception("Background stream close failed")
