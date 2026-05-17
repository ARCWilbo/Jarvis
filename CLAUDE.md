# CLAUDE.md

# Jarvis Voice Assistant — System Specification

## Goal

Build a lightweight local voice assistant named "Jarvis" that continuously listens in the background for the wake word:

    "jarvis"

Once detected:

1. Start recording the user's speech
2. Continue recording until:
   - 15 seconds max duration
   - OR 2 seconds of silence detected
3. Transcribe the speech to text
4. Print the transcription to terminal
5. Save interaction into a JSON log file with:
   - timestamp
   - raw transcription
   - duration
   - confidence (if available)

The system should run continuously with low latency and low CPU usage.

---

# Core Requirements

## Wake Word Detection

The assistant should:

- Continuously monitor microphone audio
- Detect the keyword:

      "jarvis"

- Ignore all other speech
- Wake word detection should be:
  - fast
  - lightweight
  - non-blocking

Preferred libraries:

- pvporcupine
- openWakeWord
- whisper-triggered VAD pipeline

Preferred wake engine:

- Porcupine

---

# Recording Logic

After wake word detection:

## Start Recording

Begin capturing microphone input immediately.

## Stop Conditions

Stop recording when EITHER:

### A.

15 seconds elapsed

OR

### B.

2 continuous seconds of silence detected

Silence detection should use:

- RMS energy
- VAD (preferred)
- Silero VAD
- WebRTC VAD

---

# Transcription

Transcribe recorded audio locally.

Preferred models:

1. faster-whisper
2. whisper.cpp
3. openai-whisper

Preferred:

- faster-whisper small.en

Requirements:

- low latency
- streaming-friendly
- CPU-compatible
- Apple Silicon support

---

# JSON Logging

Store all successful interactions in:

    logs/interactions.json

Format:

```json
[
  {
    "timestamp": "2026-05-16T14:22:11",
    "transcription": "open tradingview and search spy",
    "duration_seconds": 4.82,
    "wake_word": "jarvis"
  }
]
```

Append new interactions continuously.

Also save raw WAV recordings in:

```
recordings/
```

Filename format:

```
YYYYMMDD_HHMMSS.wav
```

---

# Project Structure

```
Jarvis/
│
├── main.py
├── config.py
├── requirements.txt
│
├── audio/
│ ├── listener.py
│ ├── recorder.py
│ ├── vad.py
│ └── wakeword.py
│
├── transcription/
│ └── whisper_engine.py
│
├── logging/
│ └── json_logger.py
│
├── recordings/
│
├── logs/
│ └── interactions.json
│
└── utils/
└── time_utils.py
```

---

# System Behavior

The assistant should:

- run forever until CTRL+C
- recover gracefully from audio errors
- avoid memory leaks
- avoid blocking the listener loop
- use threads or async where appropriate

Preferred architecture:

- background listener thread
- event queue
- recorder worker
- transcription worker

---

# Audio Settings

Use:

- mono audio
- 16kHz sample rate
- int16 PCM

Preferred libraries:

- sounddevice
- pyaudio
- numpy

---

# Silence Detection

Use VAD-based stopping.

Preferred:

- Silero VAD

Fallback:

- RMS threshold

Recording should stop after:

```
2 seconds of continuous silence
```

NOT cumulative silence.

---

# Terminal Output

Example:

[JARVIS ACTIVE]

Listening for wake word...

Wake word detected.

Recording...

Transcription:

> open tradingview and search spy

Saved:

- recordings/20260516_142211.wav
- logs/interactions.json

---

# Performance Goals

Target:

- wake latency < 300ms
- transcription latency < 2s
- CPU efficient
- works on:
  - MacBook Apple Silicon
  - Raspberry Pi 5

---

# Future Extensions

The architecture should support future modules:

- ChatGPT API calls
- browser automation
- desktop automation
- Home Assistant integration
- speaker verification
- TTS responses
- streaming transcription
- GUI overlay
- multi-agent orchestration

Design all components modularly.

---

# Code Quality

Requirements:

- typed Python
- clean modular architecture
- dataclasses where useful
- minimal global state
- robust exception handling
- logging module usage
- reusable components

Avoid:

- giant monolithic scripts
- blocking infinite loops
- hardcoded paths
- duplicated logic

---

# Preferred Dependencies

- pvporcupine
- sounddevice
- numpy
- scipy
- faster-whisper
- silero-vad
- torch
- webrtcvad

---

# Expected Workflow

1. Launch assistant

2. Assistant waits silently

3. User says:

   ```
   "jarvis"
   ```

4. Assistant starts recording

5. User speaks command

6. Silence detected OR 15s elapsed

7. Audio transcribed

8. Result printed

9. JSON log updated

10. Return to listening state

---

# Success Criteria

The project is successful if:

- wake word reliably triggers
- recording automatically stops correctly
- transcriptions are accurate
- logs are persisted correctly
- system can run continuously for hours
- architecture is extensible for future AI tooling
