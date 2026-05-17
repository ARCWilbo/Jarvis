# Jarvis — Local Voice Assistant

A lightweight, fully local voice assistant that listens for a wake word, records your command, transcribes it with Whisper, and logs every interaction. No cloud APIs required. Runs continuously in the background with low CPU usage.

---

## How It Works

1. Jarvis starts and waits silently for the wake phrase **"hey jarvis"**
2. Wake word is detected via **openWakeWord** (ONNX model, runs on CPU)
3. Microphone recording begins immediately
4. Recording stops when either:
   - **2 seconds of continuous silence** is detected (via Silero VAD)
   - **15 seconds** of total recording time elapses
5. Audio is transcribed locally using **faster-whisper** (`small.en` model)
6. Transcription is printed to the terminal
7. The WAV file is saved to `recordings/` and the interaction is appended to `logs/interactions.json`
8. Jarvis returns to listening

---

## Project Structure

```
Jarvis/
├── main.py                    # Entry point — wires everything together
├── config.py                  # All config as typed dataclasses
├── requirements.txt
│
├── audio/
│   ├── listener.py            # Main loop: background listener thread + event queue
│   ├── recorder.py            # Buffers post-wake audio; handles stop conditions
│   ├── vad.py                 # Silero VAD with RMS energy fallback
│   └── wakeword.py            # openWakeWord hey_jarvis detector
│
├── transcription/
│   └── whisper_engine.py      # faster-whisper wrapper with device auto-detection
│
├── log_manager/
│   └── json_logger.py         # Appends interactions to JSON log
│
├── utils/
│   └── time_utils.py          # Timestamp helpers
│
├── actions/
│   └── Launch_charts.sh       # Shell action scripts triggered by voice commands
│
├── recordings/                # WAV files (YYYYMMDD_HHMMSS.wav)
└── logs/
    └── interactions.json      # Persistent interaction log
```

---

## Requirements

- Python 3.10+
- macOS (Apple Silicon supported) or Linux
- Working microphone

Install dependencies:

```bash
pip install -r requirements.txt
```

**Dependencies:**

| Package | Purpose |
|---|---|
| `openwakeword` | Wake word detection (hey_jarvis ONNX model) |
| `sounddevice` | Microphone audio capture |
| `numpy` / `scipy` | Audio processing |
| `faster-whisper` | Local speech-to-text transcription |
| `silero-vad` | Neural voice activity detection |
| `torch` | Required by Silero VAD |
| `webrtcvad` | WebRTC VAD (available as fallback) |

---

## Running

```bash
python main.py
```

Example terminal output:

```
[JARVIS ACTIVE]
Listening for wake word...

Wake word detected.
Recording...

Transcription:
> open tradingview and search spy

Saved:
  recordings/20260516_142211.wav
  logs/interactions.json
```

Press **CTRL+C** to shut down cleanly.

---

## Configuration

All settings live in [config.py](config.py) as typed dataclasses — no config files to edit, just change the defaults.

| Setting | Default | Description |
|---|---|---|
| `sample_rate` | `16000` | Audio sample rate (Hz) |
| `channels` | `1` | Mono audio |
| `blocksize` | `512` | Samples per audio callback |
| `max_duration_seconds` | `15.0` | Max recording length |
| `silence_duration_seconds` | `2.0` | Silence threshold to stop recording |
| `model_size` | `small.en` | Whisper model (tiny/base/small/medium) |
| `device` | `auto` | Inference device (auto-detects CUDA or CPU) |
| `compute_type` | `auto` | float16 on GPU, int8 on CPU |

---

## Interaction Log Format

Every transcribed command is appended to `logs/interactions.json`:

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

The log and all recordings are cleared at startup each session.

---

## Architecture

The system uses a **producer-consumer thread model** to avoid blocking the audio callback:

- **Listener thread** — runs the sounddevice input stream; feeds audio frames to the wake word detector and, after activation, to the recorder
- **Event queue** — decouples audio capture from transcription
- **Transcription worker** — pulls completed recordings off the queue and runs Whisper inference

This keeps the audio callback non-blocking and prevents dropped frames or latency spikes during transcription.

---

## Performance Targets

| Metric | Target |
|---|---|
| Wake word latency | < 300 ms |
| Transcription latency | < 2 s |
| Platform | MacBook Apple Silicon, Raspberry Pi 5 |
| CPU usage | Low (idle listening) |

---

## Future Possible Additions

### AI & Language
- **ChatGPT / Claude API integration** — send transcriptions to an LLM and speak the response back
- **Streaming transcription** — real-time Whisper output as you speak, not after silence
- **Intent classification** — route commands to the right handler without exact phrase matching
- **Conversation memory** — maintain context across multiple commands in a session

### Voice & Audio
- **TTS responses** — Jarvis speaks back using a local TTS engine (Coqui, Piper, or macOS `say`)
- **Speaker verification** — only respond to the enrolled user's voice
- **Custom wake word training** — replace "hey jarvis" with any phrase using openWakeWord fine-tuning
- **Multi-microphone support** — beamforming or device selection for noisy environments

### Automation & Actions
- **Browser automation** — execute web commands via Playwright (open URLs, search, click)
- **Desktop automation** — control apps via AppleScript / pyautogui
- **Home Assistant integration** — control smart home devices by voice
- **Shell command execution** — run terminal commands from spoken input
- **App launcher** — open applications by name

### Interface
- **GUI overlay** — floating status indicator showing listening / recording / transcribing state
- **Web dashboard** — review interaction history, replay recordings, tweak config in a browser UI
- **Notification support** — macOS or Linux desktop notifications on trigger/result

### Infrastructure
- **Multi-agent orchestration** — route commands to specialized sub-agents (research, calendar, code)
- **Plugin system** — drop-in action modules without modifying core code
- **Remote trigger** — wake Jarvis from a hotkey, button, or HTTP call instead of (or in addition to) voice
- **Raspberry Pi deployment** — headless always-on listener with minimal resource footprint
