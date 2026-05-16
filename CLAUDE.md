# CLAUDE.md

## Project Overview

Jarvis is a local voice-activated AI assistant running on a Raspberry Pi 5 or MacBook.

The assistant should:

- Continuously listen for a wake word ("Jarvis")
- Convert speech → text
- Send requests to the OpenAI Chat API
- Speak responses aloud
- Maintain lightweight conversation memory
- Support future expansion into robotics, vision, and home automation

Primary design goals:

- Low latency
- Modular architecture
- Clean async event-driven code
- Easy extensibility
- Human-like interaction loop
- Stable long-running local execution

---

# Core System Architecture

```text
Microphone
    ↓
Wake Word Detection
    ↓
Speech-to-Text
    ↓
Conversation Manager
    ↓
LLM API Call
    ↓
Response Parser
    ↓
Text-to-Speech
    ↓
Speaker Output
```

---

# Tech Stack

## Language

- Python 3.11+

## Speech Recognition

Preferred:

- faster-whisper

Fallback:

- OpenAI transcription API

## LLM

Preferred:

- OpenAI Responses API

## Text-to-Speech

Preferred:

- OpenAI TTS

Fallback:

- pyttsx3

## Audio

- sounddevice
- pyaudio
- scipy

## Async Runtime

- asyncio

## Environment

- dotenv

## Vision (future)

- OpenCV

## Robotics (future)

- gpiozero
- RPi.GPIO

---

# High-Level Folder Structure

```text
jarvis/
│
├── main.py
├── CLAUDE.md
├── requirements.txt
├── .env
│
├── config/
│   └── settings.py
│
├── audio/
│   ├── microphone.py
│   ├── playback.py
│   ├── recorder.py
│   └── wakeword.py
│
├── speech/
│   ├── transcribe.py
│   └── tts.py
│
├── llm/
│   ├── client.py
│   ├── prompts.py
│   └── memory.py
│
├── vision/
│   └── camera.py
│
├── robotics/
│   ├── servos.py
│   ├── leds.py
│   └── motors.py
│
├── utils/
│   ├── logger.py
│   ├── timing.py
│   └── helpers.py
│
└── data/
    ├── conversations/
    └── audio_cache/
```

---

# Coding Principles

## General Rules

- Prefer readability over cleverness
- Use type hints everywhere
- Avoid global mutable state
- Keep functions small and pure when possible
- Use async/await for all blocking IO
- Separate hardware logic from AI logic
- Every module should have a single responsibility

---

# Performance Priorities

Prioritize:

1. Low audio latency
2. Fast wake-word detection
3. Streaming responses
4. Interruptibility
5. Stable memory usage

Avoid:

- Loading large local LLMs
- Blocking main event loop
- Excessive threading
- Overengineering

---

# Wake Word Behavior

The assistant should:

- Passively listen continuously
- Activate only after hearing:
  - "Jarvis"
  - configurable future wake words

- Ignore background speech
- Debounce repeated activations

Future support:

- Porcupine wake word engine

---

# Conversation Behavior

Jarvis should:

- Be concise by default
- Sound intelligent but conversational
- Avoid overly verbose answers
- Respond quickly
- Maintain short conversational memory
- Support interruption while speaking

---

# Memory System

Conversation memory should:

- Store recent exchanges
- Summarize old context periodically
- Persist lightweight session history locally

Avoid:

- Huge vector DBs initially
- Premature RAG systems
- Complex orchestration frameworks

---

# API Guidelines

## OpenAI

Use:

- latest lightweight chat model
- streaming responses when possible

Never:

- hardcode API keys
- expose secrets in logs

Environment variables:

```env
OPENAI_API_KEY=...
```

---

# Audio Pipeline

Preferred pipeline:

```text
Mic Input
→ VAD
→ Wake Word
→ Record Command
→ Whisper Transcription
→ GPT Response
→ TTS Audio Stream
→ Speaker
```

Target latency:

- Wake detection: <200ms
- Transcription: <2s
- First spoken token: <1s after response starts

---

# Logging

Use structured logs.

Every major subsystem should log:

- startup
- shutdown
- errors
- latency
- API timings

Avoid excessive console spam.

---

# Future Features

## Near-Term

- Streaming TTS
- Interrupt detection
- Better memory
- Webcam integration
- Local command execution

## Medium-Term

- Servo head tracking
- Facial recognition
- Smart home integration
- Desktop control

## Long-Term

- Autonomous robotics
- Multi-agent planning
- Local small models
- Full embodied assistant

---

# Robotics Philosophy

Do NOT tightly couple robotics to LLM logic.

The LLM should:

- issue high-level intents

Hardware layer should:

- safely execute commands

Example:

```text
LLM:
"Turn head left"

Robotics Layer:
servo_controller.rotate(30)
```

---

# Development Style

Preferred:

- incremental development
- test each subsystem independently
- CLI-first debugging
- modular iteration

Avoid:

- giant rewrites
- premature abstractions
- unnecessary frameworks

---

# First MVP Goals

Version 1 should only do:

1. Listen
2. Detect wake word
3. Transcribe speech
4. Query GPT
5. Speak response

Nothing else.

Do NOT add:

- robotics
- databases
- ROS
- local LLM hosting
- distributed systems

until the MVP is stable.

---

# Example MVP Interaction

User:
"Jarvis, explain transformers."

Pipeline:

- wake word detected
- audio recorded
- speech transcribed
- GPT queried
- response spoken aloud

---

# Preferred Libraries

## Strongly Preferred

- asyncio
- faster-whisper
- openai
- sounddevice
- numpy

## Avoid Initially

- ROS
- LangChain
- Kubernetes
- Docker orchestration
- heavy agent frameworks

---

# Deployment Targets

Primary:

- Raspberry Pi 5

Secondary:

- MacBook Apple Silicon

Future:

- Jetson Orin

---

# Code Quality

All production code should:

- pass ruff
- pass mypy
- avoid duplicated logic
- include docstrings
- include timing instrumentation

---

# Final Philosophy

Jarvis should feel:

- responsive
- intelligent
- calm
- reliable
- local-first
- extensible

The system should prioritize simplicity and iteration speed over maximal complexity.

```

```
