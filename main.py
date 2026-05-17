from __future__ import annotations

import logging
import signal
import sys

from config import JarvisConfig
from audio.listener import JarvisListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Suppress noisy third-party loggers
for _noisy in ("httpx", "huggingface_hub", "faster_whisper", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def _clear_session_data(config: JarvisConfig) -> None:
    """Delete all recordings and reset the interaction log before each run."""
    recordings_dir = config.recording.recordings_dir
    if recordings_dir.exists():
        for f in recordings_dir.glob("*.wav"):
            f.unlink()

    log_path = config.log.logs_dir / config.log.interactions_file
    if log_path.exists():
        log_path.write_text("[]")


def main() -> None:
    config = JarvisConfig()
    _clear_session_data(config)
    listener = JarvisListener(config)

    def handle_shutdown(sig, frame) -> None:
        print("\n\nShutting down Jarvis...")
        listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        listener.start()
    except KeyboardInterrupt:
        handle_shutdown(None, None)
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
