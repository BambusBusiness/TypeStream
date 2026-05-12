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


# Windows lists every physical mic once per host API (MME / DirectSound /
# WASAPI / WDM-KS). We pick a single host API to display so the user doesn't
# see five "Mikrofon (USB)" entries — preferring WASAPI for low-latency capture.
_PREFERRED_HOSTAPIS = (
    "Windows WASAPI",
    "Windows DirectSound",
    "MME",
    "Windows WDM-KS",
    "Core Audio",
    "ALSA",
    "JACK Audio Connection Kit",
    "PulseAudio",
)

# Pseudo-devices that are just routing aliases for the system default —
# we already expose "Systemstandard" as the first combo entry, so these
# are noise.
_ALIAS_NEEDLES = (
    "sound mapper",
    "primary sound",
    "primärer sound",
)


def _is_alias_device(name: str) -> bool:
    n = name.lower()
    return any(needle in n for needle in _ALIAS_NEEDLES)


def _preferred_hostapi_index() -> int | None:
    """Pick the first host API that exposes at least one input device. Returns
    None on platforms where the preference list doesn't match any host API
    (older sounddevice / unusual driver setups) — caller then falls back to
    listing across all host APIs."""
    try:
        hostapis = sd.query_hostapis()
        devices = sd.query_devices()
    except Exception:
        return None
    api_by_name = {h.get("name", ""): i for i, h in enumerate(hostapis)}
    for pref in _PREFERRED_HOSTAPIS:
        i = api_by_name.get(pref)
        if i is None:
            continue
        if any(
            d.get("max_input_channels", 0) > 0 and d.get("hostapi") == i
            for d in devices
        ):
            return i
    return None


def list_input_devices() -> list[tuple[str, str]]:
    """Return (device_name, display_label) tuples for the unique input devices
    of the preferred host API, with sound-mapper aliases stripped."""
    try:
        devices = sd.query_devices()
    except Exception as e:
        log.warning("Failed to query audio devices: %s", e)
        return []
    api = _preferred_hostapi_index()
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for d in devices:
        if d.get("max_input_channels", 0) <= 0:
            continue
        if api is not None and d.get("hostapi") != api:
            continue
        name = (d.get("name") or "").strip()
        if not name or name in seen:
            continue
        if _is_alias_device(name):
            continue
        seen.add(name)
        result.append((name, name))
    return result


def resolve_input_device(name: str) -> int | None:
    """Map a saved device name to a concrete sounddevice index. Prefers the
    same host API we listed from so the saved selection actually opens that
    backend; falls back to any matching device if WASAPI drivers were removed
    between sessions."""
    if not name:
        return None
    try:
        devices = sd.query_devices()
    except Exception:
        return None
    api = _preferred_hostapi_index()
    if api is not None:
        for i, d in enumerate(devices):
            if (
                d.get("max_input_channels", 0) > 0
                and d.get("hostapi") == api
                and (d.get("name") or "").strip() == name
            ):
                return i
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0 and (d.get("name") or "").strip() == name:
            return i
    return None


class AudioRecorder:
    def __init__(self, input_device: str = ""):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._capturing = False
        self._input_device = input_device

    def is_recording(self) -> bool:
        return self._stream is not None

    def set_input_device(self, name: str) -> None:
        self._input_device = name

    def prewarm(self) -> None:
        """Open and immediately close a short InputStream so the WASAPI driver
        is initialized before the first real recording. Cuts cold-start latency
        on the first hotkey press from ~hundreds of ms (sometimes seconds when
        the endpoint is idle-suspended) down to driver wake-up time."""
        device_index = resolve_input_device(self._input_device)
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                latency="low",
                device=device_index,
            )
            stream.start()
            stream.stop()
            stream.close()
            log.info("Recorder prewarmed (device=%s)", device_index)
        except Exception as e:
            log.debug("Recorder prewarm failed: %s", e)

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks = []
            self._capturing = True
        device_index = resolve_input_device(self._input_device)
        if self._input_device and device_index is None:
            log.warning(
                "Saved input device %r not found — falling back to system default.",
                self._input_device,
            )
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                latency="low",
                device=device_index,
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
