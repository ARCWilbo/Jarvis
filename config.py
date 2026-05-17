from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    blocksize: int = 512  # samples per audio callback — matches Silero VAD frame size


@dataclass
class WakeWordConfig:
    keyword: str = "jarvis"


@dataclass
class RecordingConfig:
    max_duration_seconds: float = 15.0
    silence_duration_seconds: float = 2.0
    recordings_dir: Path = field(default_factory=lambda: Path("recordings"))


@dataclass
class TranscriptionConfig:
    model_size: str = "small.en"
    device: str = "auto"
    compute_type: str = "auto"


@dataclass
class LogConfig:
    logs_dir: Path = field(default_factory=lambda: Path("logs"))
    interactions_file: str = "interactions.json"


@dataclass
class JarvisConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    log: LogConfig = field(default_factory=LogConfig)
