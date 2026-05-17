from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from config import JarvisConfig

logger = logging.getLogger(__name__)


class WhisperEngine:
    """faster-whisper transcription engine with lazy model loading."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._model = None
        self._sample_rate = config.audio.sample_rate
        self._load_model()

    def _load_model(self) -> None:
        from faster_whisper import WhisperModel

        cfg = self._config.transcription
        device = cfg.device
        compute_type = cfg.compute_type

        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        logger.info(
            "Loading faster-whisper '%s' on %s (%s)...",
            cfg.model_size,
            device,
            compute_type,
        )
        self._model = WhisperModel(cfg.model_size, device=device, compute_type=compute_type)
        logger.info("Whisper model ready.")

    def transcribe_array(self, audio: np.ndarray) -> str:
        """Transcribe raw int16 PCM array. Returns joined transcript text."""
        audio_float = audio.astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(audio_float, beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
