from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonLogger:
    """Appends voice interactions to a JSON array log file."""

    def __init__(self, config) -> None:
        self._log_path = config.log.logs_dir / config.log.interactions_file
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.write_text("[]")

    def log(
        self,
        *,
        timestamp: str,
        transcription: str,
        duration_seconds: float,
        wake_word: str,
    ) -> None:
        try:
            entries: list = json.loads(self._log_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            entries = []

        entries.append(
            {
                "timestamp": timestamp,
                "transcription": transcription,
                "duration_seconds": round(duration_seconds, 2),
                "wake_word": wake_word,
            }
        )

        self._log_path.write_text(json.dumps(entries, indent=2))
        logger.debug("Interaction logged at %s", timestamp)
