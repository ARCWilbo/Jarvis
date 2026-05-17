from __future__ import annotations

import logging
import time
import wave
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import numpy as np

from audio.vad import VADProcessor

if TYPE_CHECKING:
    from config import JarvisConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Buffers microphone audio after wake word; stops on silence or max duration."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._vad = VADProcessor(config.audio.sample_rate)
        self._chunks: list[np.ndarray] = []
        self._start_time: float = 0.0
        self._silence_start: Optional[float] = None
        self._recording: bool = False

    def start(self) -> None:
        self._chunks = []
        self._start_time = time.monotonic()
        self._silence_start = None
        self._recording = True
        self._vad.reset()

    def add_chunk(self, chunk: np.ndarray) -> None:
        if not self._recording:
            return
        self._chunks.append(chunk.flatten().copy())
        if self._vad.is_speech(chunk):
            self._silence_start = None
        elif self._silence_start is None:
            self._silence_start = time.monotonic()

    def should_stop(self) -> bool:
        if not self._recording:
            return False
        elapsed = time.monotonic() - self._start_time
        if elapsed >= self._config.recording.max_duration_seconds:
            return True
        if (
            self._silence_start is not None
            and (time.monotonic() - self._silence_start)
            >= self._config.recording.silence_duration_seconds
        ):
            return True
        return False

    def stop(self) -> tuple[np.ndarray, float]:
        """Stop recording. Returns (audio_int16, duration_seconds)."""
        self._recording = False
        if not self._chunks:
            return np.array([], dtype=np.int16), 0.0
        audio = np.concatenate(self._chunks).astype(np.int16)
        duration = len(audio) / self._config.audio.sample_rate
        return audio, duration

    def save_wav(self, audio: np.ndarray, filepath: Path) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(filepath), "wb") as wf:
            wf.setnchannels(self._config.audio.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self._config.audio.sample_rate)
            wf.writeframes(audio.tobytes())
        logger.debug("WAV saved: %s", filepath)
