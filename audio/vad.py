from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class VADProcessor:
    """Voice Activity Detection — Silero VAD with RMS energy fallback."""

    # Silero VAD expects exactly 512 samples per chunk at 16 kHz
    SILERO_CHUNK_SIZE = 512

    def __init__(self, sample_rate: int = 16000) -> None:
        self._sample_rate = sample_rate
        self._model: Optional[object] = None
        self._torch = None
        self._mode: str = "rms"
        self._init_silero()

    def _init_silero(self) -> None:
        try:
            import torch
            from silero_vad import load_silero_vad

            self._model = load_silero_vad()
            self._torch = torch
            self._mode = "silero"
            logger.info("VAD: Silero VAD initialized")
        except Exception as exc:
            logger.warning("Silero VAD unavailable (%s) — using RMS fallback", exc)
            self._mode = "rms"

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        chunk = audio_chunk.flatten()
        if self._mode == "silero":
            return self._silero_is_speech(chunk)
        return self._rms_is_speech(chunk)

    def _silero_is_speech(self, chunk: np.ndarray) -> bool:
        try:
            # Pad or trim to exactly SILERO_CHUNK_SIZE
            if len(chunk) < self.SILERO_CHUNK_SIZE:
                chunk = np.pad(chunk, (0, self.SILERO_CHUNK_SIZE - len(chunk)))
            elif len(chunk) > self.SILERO_CHUNK_SIZE:
                chunk = chunk[: self.SILERO_CHUNK_SIZE]

            audio_float = chunk.astype(np.float32) / 32768.0
            tensor = self._torch.from_numpy(audio_float)
            confidence: float = self._model(tensor, self._sample_rate).item()
            return confidence > 0.5
        except Exception as exc:
            logger.debug("Silero inference failed: %s", exc)
            return self._rms_is_speech(chunk)

    @staticmethod
    def _rms_is_speech(chunk: np.ndarray, threshold: float = 500.0) -> bool:
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        return rms > threshold

    def reset(self) -> None:
        if self._mode == "silero" and self._model is not None:
            try:
                self._model.reset_states()
            except Exception:
                pass
