# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPi Video Streamer + Jetson AI Pipeline + Voice AI Kitchen Assistant — streams live MJPEG video from a Raspberry Pi camera (`sender.py`) to a base station RPi which forwards frames to a Jetson Orin Nano (`jetson_processor.py`) for AI processing. The Jetson runs optional YOLOv8 object detection and periodic Ollama VLM scene analysis, streaming results back to the base station GUI. An ESP32 with microphone and speaker provides a voice interface: the user asks cooking questions, which are transcribed (ElevenLabs STT), answered by Claude (using VLM scene context), and spoken back (ElevenLabs TTS). Built for TreeHacks 2026.

## Architecture

Three devices communicating over UDP:

- **sender.py** (Camera Pi): Uses `picamera2` to capture video, encodes as MJPEG, sends each JPEG frame over UDP with a 4-byte big-endian length header.
- **receiver_jetson.py** (Base Station Pi): Receives camera frames, displays them, forwards to Jetson, receives processed frames back, and displays both side-by-side in a Tkinter GUI. Also receives VLM analysis text and shows it in a scrollable log widget. (Video only — see `receiver_jetson_full.py` for the unified version with voice AI.)
- **receiver_jetson_full.py** (Base Station Pi): Unified version of `receiver_jetson.py` that adds the voice AI pipeline. Receives ESP32 mic audio, runs Silero VAD, transcribes via ElevenLabs STT, queries Claude with VLM context, generates TTS, and streams audio back to ESP32.
- **jetson_processor.py** (Jetson Orin Nano): Receives forwarded frames, optionally runs YOLOv8n TensorRT detection, returns annotated frames. Periodically sends frames to local Ollama `qwen3-vl:2b` VLM for scene analysis and streams results back via UDP.

### Port allocation

| Port | Direction | Content |
|------|-----------|---------|
| 9000 | Camera Pi → Base Station | Raw JPEG frames (UDP) |
| 9001 | Base Station → Jetson | Forwarded JPEG frames (UDP) |
| 9002 | Jetson → Base Station | Annotated JPEG frames (UDP) |
| 9003 | Jetson → Base Station | VLM analysis text (plain UTF-8, UDP) |
| 12345 | ESP32 → Base Station | Raw mic audio (16-bit mono PCM, 44.1kHz, UDP) |
| 12345 | Base Station → ESP32 | TTS playback audio (16-bit stereo PCM, 44.1kHz, UDP) |

### Wire protocol

`[4-byte big-endian uint32 frame length][JPEG frame bytes]` per frame on ports 9000/9001/9002. Port 9003 sends plain UTF-8 text datagrams (no length header).

### Threading model (Jetson)

```
Main thread (full frame rate)        VLM daemon thread (every ~5s)
─────────────────────────────        ────────────────────────────
recv UDP:9001                        jpeg = queue.get()
optional YOLO detect + annotate      result = query_ollama(jpeg)
encode + send UDP:9002               log to file + print
every 5s: queue.put_nowait(jpeg)     sendto UDP:9003
```

The VLM thread has zero impact on the main loop — `queue.put_nowait` is non-blocking.

## Key files

| File | Runs on | Purpose |
|------|---------|---------|
| `sender.py` | Camera Pi | Captures and streams MJPEG frames |
| `receiver_jetson.py` | Base Station Pi | GUI: displays raw + processed feeds, VLM log (video only) |
| `receiver_jetson_full.py` | Base Station Pi | Unified GUI + Voice AI pipeline (STT → Claude → TTS) |
| `jetson_processor.py` | Jetson Orin Nano | YOLO detection (optional) + VLM analysis |
| `receiver.py` | Base Station Pi | Legacy simple receiver (no Jetson pipeline) |
| `audio_processing/esp32_stt.py` | Base Station Pi | Standalone ESP32 STT with Silero VAD |
| `audio_processing/tts_to_esp32.py` | Base Station Pi | Standalone TTS audio sender to ESP32 |

## Voice AI Pipeline

The full voice assistant flow (implemented in `receiver_jetson_full.py`):

```
ESP32 Mic → UDP:12345 → Base Station (Silero VAD detects speech)
  → ElevenLabs STT (scribe_v2) → transcribed text
  → Claude API (claude-opus-4-6, with VLM scene log as context)
  → ElevenLabs TTS (voice JBFqnCBsd6RMkjVDRZzb, eleven_multilingual_v2)
  → ffmpeg MP3→WAV → UDP → ESP32 Speaker
```

The user speaks a cooking question into the ESP32 microphone. Silero VAD detects when speech starts and ends. The recorded audio is sent to ElevenLabs STT for transcription. The transcribed question, along with the recent VLM scene analysis log from the Jetson (already buffered in `_vlm_messages`), is sent to Claude as a conversational kitchen helper. Claude's concise response is converted to speech via ElevenLabs TTS and streamed back to the ESP32 speaker.

### Threading model (Base Station, receiver_jetson_full.py)

```
Camera recv thread     Jetson recv thread     VLM recv thread
──────────────────     ──────────────────     ───────────────
recv UDP:9000          recv UDP:9002          recv UDP:9003
decode + display       decode + display       append to log
forward to Jetson

Audio recv thread               Voice query thread (spawned per utterance)
─────────────────               ────────────────────────────────────────
recv UDP:12345                  STT (ElevenLabs)
Silero VAD                      Claude API (with VLM context)
on speech end → spawn thread    TTS (ElevenLabs)
                                stream audio → ESP32
```

## Dependencies

### Camera Pi
```bash
sudo apt-get install -y python3-picamera2
```

### Base Station Pi
```bash
# System packages (video pipeline)
sudo apt-get install -y python3-opencv python3-numpy python3-pil python3-pil.imagetk python3-tk

# Python packages (voice AI pipeline, for receiver_jetson_full.py)
# Note: torch==2.6.0 required on RPi 4 (Cortex-A72); newer versions crash
pip3 install anthropic elevenlabs python-dotenv scipy "torch==2.6.0" silero-vad

# ffmpeg (for TTS MP3→WAV conversion)
sudo apt-get install -y ffmpeg
```

### Jetson Orin Nano
```bash
# OpenCV + NumPy (system packages or pip)
sudo apt-get install -y python3-opencv python3-numpy

# YOLOv8 (only needed if using --yolo flag)
pip3 install ultralytics

# Ollama (for VLM analysis)
# Install from https://ollama.com, then:
ollama pull qwen3-vl:2b
```

### Environment variables

Create a `.env` file in the project root (already in `.gitignore`):
```
ANTHROPIC_API_KEY=<your-anthropic-api-key>
ELEVENLABS_API_KEY=<your-elevenlabs-api-key>
```

## Running

See `RUN_PIPELINE.md` for full step-by-step instructions.

Quick start (video only):
```bash
# 1. Jetson (start first)
python3 jetson_processor.py --port 9001 --return-port 9002

# 2. Base Station Pi
python3 receiver_jetson.py --port 9000 --jetson-host <JETSON_IP>

# 3. Camera Pi
python3 sender.py --host <BASE_STATION_IP> --port 9000
```

Full pipeline (video + voice AI):
```bash
# 1. Jetson (start first)
python3 jetson_processor.py --port 9001 --return-port 9002

# 2. Base Station Pi (unified receiver with voice AI)
python3 receiver_jetson_full.py --port 9000 --jetson-host <JETSON_IP> \
    --esp32-host <ESP32_IP>

# 3. Camera Pi
python3 sender.py --host <BASE_STATION_IP> --port 9000
```

### Notable flags

- `--yolo` on `jetson_processor.py` enables YOLOv8 detection (disabled by default)
- `--vlm-interval` on `jetson_processor.py` controls seconds between VLM queries (default 5)
- `--audio-port` on `receiver_jetson_full.py` sets ESP32 mic listen port (default 12345)
- `--esp32-host` on `receiver_jetson_full.py` sets ESP32 IP for TTS playback (default 172.20.10.12)
- Press `q` or `Escape` in the receiver GUI to quit. `r` saves raw frame, `p` saves processed.

## DS18B20 Temperature Sensor

- **ds18b20.py**: Reads temperature from a DS18B20 sensor over the 1-Wire bus on BCM GPIO 17 (physical pin 11).
- Uses kernel modules `w1-gpio` and `w1-therm` via sysfs (`/sys/bus/w1/devices/28-*/w1_slave`).
- Wiring: data pin → physical pin 11 (BCM 17), 4.7kΩ pull-up to 3.3V.
- Requires `dtoverlay=w1-gpio,gpiopin=17` in `/boot/config.txt` for persistent boot config.

```bash
sudo python3 ds18b20.py
```

## Platform

- **Camera Pi**: Raspberry Pi with camera module (ARM/Linux)
- **Base Station Pi**: Raspberry Pi with display (monitor, VNC, or X forwarding) for Tkinter GUI
- **Jetson**: NVIDIA Jetson Orin Nano (ARM/Linux, CUDA/TensorRT for YOLO, Ollama for VLM)
