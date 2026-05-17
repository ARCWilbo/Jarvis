from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from config import JarvisConfig

logger = logging.getLogger(__name__)

# openWakeWord expects 80 ms chunks @ 16 kHz
FRAME_LENGTH = 1280


class WakeWordDetector:
    """Detects 'hey jarvis' using openWakeWord's ONNX hey_jarvis model."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._oww_model = None
        self._frame_length = FRAME_LENGTH
        self._init()

    def _init(self) -> None:
        import openwakeword
        from openwakeword.model import Model

        # Only download if the model file is missing (suppresses bars on subsequent runs)
        model_path = os.path.join(
            os.path.dirname(openwakeword.__file__),
            "resources", "models", "hey_jarvis_v0.1.onnx",
        )
        if not os.path.exists(model_path):
            openwakeword.utils.download_models(model_names=["hey_jarvis"])

        self._oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        logger.info("Wake word engine: openWakeWord hey_jarvis (frame_length=%d)", self._frame_length)

    @property
    def frame_length(self) -> int:
        return self._frame_length

    def process(self, frame: np.ndarray) -> bool:
        """Return True if hey_jarvis detected in this 80 ms frame."""
        self._oww_model.predict(frame.flatten().astype(np.int16))
        score = float(self._oww_model.prediction_buffer.get("hey_jarvis", [0.0])[-1])
        return score > 0.5

    def reset(self) -> None:
        """Clear OWW's internal state so stale scores don't retrigger detection."""
        if self._oww_model is None:
            return
        # Clear scored history
        for key in self._oww_model.prediction_buffer:
            self._oww_model.prediction_buffer[key] = []
        # Reset the feature model's rolling mel-spectrogram buffer
        try:
            self._oww_model.reset()
        except Exception:
            pass  # older OWW versions may not have this method

    def cleanup(self) -> None:
        pass
