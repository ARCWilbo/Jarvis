from __future__ import annotations

import logging
import queue
import re
import threading
import sys
import time
import subprocess
from typing import TYPE_CHECKING

import numpy as np

from audio.recorder import AudioRecorder
from audio.wakeword import WakeWordDetector
from log_manager.json_logger import JsonLogger
from transcription.whisper_engine import WhisperEngine
from utils.time_utils import now_filename, now_iso

if TYPE_CHECKING:
    from config import JarvisConfig

logger = logging.getLogger(__name__)

# Whisper hallucinates these strings when given silence or near-silence audio
_SILENCE_HALLUCINATIONS = {"thank you.", "thank you", ".", "you.", "the.", "you", "bye."}

# Seconds to ignore wake word after returning to LISTENING (prevents OWW re-trigger)
_POST_RECORD_COOLDOWN = 1.5


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation so Whisper augmentations don't break matching."""
    return re.sub(r"[^\w\s]", "", text).strip().lower()


class JarvisListener:
    """Orchestrates the full pipeline: wake word → record → transcribe → log.

    Architecture:
      sounddevice callback → audio_queue
      main processing loop  → wake word detection (LISTENING) or chunk buffering (RECORDING)
      transcription thread  → whisper inference + JSON logging (async, non-blocking)
    """

    _STATE_LISTENING = "listening"
    _STATE_RECORDING = "recording"

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._state: str = self._STATE_LISTENING
        self._stop_event = threading.Event()
        self._cooldown_until: float = 0.0  # epoch time; ignore wake word before this

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)
        self._transcription_queue: queue.Queue[tuple] = queue.Queue()
        self._execution_queue: queue.Queue[tuple] = queue.Queue()

        self._whisper = WhisperEngine(config)
        self._wake_detector = WakeWordDetector(config)
        self._recorder = AudioRecorder(config)
        self._json_logger = JsonLogger(config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        import sounddevice as sd

        print()
        print("─" * 42)
        print("  JARVIS  ·  Voice Assistant")
        print("─" * 42)
        print("  Say \"hey jarvis\" to activate.\n")

        transcription_thread = threading.Thread(
            target=self._transcription_worker, daemon=True, name="transcription-worker"
        )
        transcription_thread.start()

        execution_worker_thread = threading.Thread(
            target=self._execution_worker, daemon=True, name="execution-worker"
        )
        execution_worker_thread.start()

        def audio_callback(
            indata: np.ndarray, frames: int, time_info, status
        ) -> None:
            if status:
                logger.warning("Audio callback status: %s", status)
            try:
                self._audio_queue.put_nowait(indata.copy())
            except queue.Full:
                logger.debug("Audio queue full — dropping frame")

        stream = sd.InputStream(
            samplerate=self._config.audio.sample_rate,
            channels=self._config.audio.channels,
            dtype=self._config.audio.dtype,
            blocksize=self._config.audio.blocksize,
            callback=audio_callback,
        )

        with stream:
            self._process_loop()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_detector.cleanup()

    # ------------------------------------------------------------------
    # Internal processing loop (runs in calling thread)
    # ------------------------------------------------------------------

    def _process_loop(self) -> None:
        frame_length = self._wake_detector.frame_length
        oww_buf: list[int] = []

        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            flat: np.ndarray = chunk.flatten()

            if self._state == self._STATE_LISTENING:
                oww_buf.extend(flat.tolist())
                while len(oww_buf) >= frame_length:
                    frame = np.array(oww_buf[:frame_length], dtype=np.int16)
                    del oww_buf[:frame_length]

                    # Ignore detections during cooldown window
                    if time.monotonic() < self._cooldown_until:
                        continue

                    if self._wake_detector.process(frame):
                        oww_buf.clear()
                        self._on_wake_word()
                        break

            elif self._state == self._STATE_RECORDING:
                self._recorder.add_chunk(flat)
                if self._recorder.should_stop():
                    self._finish_recording()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_wake_word(self) -> None:
        print("  ▶  Wake word detected — recording")
        self._state = self._STATE_RECORDING
        self._recorder.start()

    def _finish_recording(self) -> None:
        audio, duration = self._recorder.stop()

        # Flush any audio that queued up during recording, reset OWW state,
        # then enforce a cooldown before the next wake word can fire.
        self._flush_audio_queue()
        self._wake_detector.reset()
        self._cooldown_until = time.monotonic() + _POST_RECORD_COOLDOWN
        self._state = self._STATE_LISTENING

        if duration < 0.3:
            logger.debug("Recording too short (%.2f s) — discarding", duration)
            return

        timestamp_iso = now_iso()
        wav_path = self._config.recording.recordings_dir / f"{now_filename()}.wav"
        # self._recorder.save_wav(audio, wav_path)
        self._transcription_queue.put((audio, duration, wav_path, timestamp_iso))

    def _flush_audio_queue(self) -> None:
        """Discard backlogged audio so OWW starts fresh on real-time input."""
        flushed = 0
        while True:
            try:
                self._audio_queue.get_nowait()
                flushed += 1
            except queue.Empty:
                break
        if flushed:
            logger.debug("Flushed %d stale audio frames from queue", flushed)

    # ------------------------------------------------------------------
    # Transcription worker (background thread)
    # ------------------------------------------------------------------

    def _transcription_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                audio, duration, wav_path, timestamp = self._transcription_queue.get(
                    timeout=0.5
                )
            except queue.Empty:
                continue

            try:
                text = self._whisper.transcribe_array(audio)

                if text.strip() and text.strip().lower() not in _SILENCE_HALLUCINATIONS:
                    print(f'\n  "{text}"\n')
                    self._json_logger.log(
                        timestamp=timestamp,
                        transcription=text,
                        duration_seconds=duration,
                        wake_word=self._config.wake_word.keyword,
                    )
                    self._execution_queue.put((text, timestamp))
                else:
                    logger.debug("Skipping hallucinated transcription: %r", text)
            except Exception as exc:
                logger.error("Transcription failed: %s", exc, exc_info=True)
            finally:
                print("  Listening...\n")

    def _execution_worker(self) -> None:
        """Placeholder for future command execution logic."""
        while not self._stop_event.is_set():
            try:
                text, timestamp = self._execution_queue.get(timeout=0.5)
                if text and text.strip():
                    command = _normalize(text)
                    if command == "launch charts":
                        # logger.info("Executing command: Launching charts...")
                        subprocess.Popen(["bash", "./commands/launch_charts.sh"])
                    elif command == "stop" or command == "exit":
                        logger.info("Executing command: Stopping Jarvis...")
                        self.stop()
                        sys.exit(0)

            except queue.Empty:
                continue
