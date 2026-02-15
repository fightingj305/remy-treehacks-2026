# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPi Video Streamer + Jetson AI Pipeline — streams live MJPEG video from a Raspberry Pi camera (`sender.py`) to a base station RPi (`receiver_jetson.py`) which forwards frames to a Jetson Orin Nano (`jetson_processor.py`) for AI processing. The Jetson runs optional YOLOv8 object detection and periodic Ollama VLM scene analysis, streaming results back to the base station GUI. Built for TreeHacks 2026.

## Architecture

Three devices communicating over UDP:

- **sender.py** (Camera Pi): Uses `picamera2` to capture video, encodes as MJPEG, sends each JPEG frame over UDP with a 4-byte big-endian length header.
- **receiver_jetson.py** (Base Station Pi): Receives camera frames, displays them, forwards to Jetson, receives processed frames back, and displays both side-by-side in a Tkinter GUI. Also receives VLM analysis text and shows it in a scrollable log widget.
- **jetson_processor.py** (Jetson Orin Nano): Receives forwarded frames, optionally runs YOLOv8n TensorRT detection, returns annotated frames. Periodically sends frames to local Ollama `qwen3-vl:2b` VLM for scene analysis and streams results back via UDP.

### Port allocation

| Port | Direction | Content |
|------|-----------|---------|
| 9000 | Camera Pi → Base Station | Raw JPEG frames (UDP) |
| 9001 | Base Station → Jetson | Forwarded JPEG frames (UDP) |
| 9002 | Jetson → Base Station | Annotated JPEG frames (UDP) |
| 9003 | Jetson → Base Station | VLM analysis text (plain UTF-8, UDP) |

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
| `receiver_jetson.py` | Base Station Pi | GUI: displays raw + processed feeds, VLM log |
| `jetson_processor.py` | Jetson Orin Nano | YOLO detection (optional) + VLM analysis |
| `receiver.py` | Base Station Pi | Legacy simple receiver (no Jetson pipeline) |

## Dependencies

### Camera Pi
```bash
sudo apt-get install -y python3-picamera2
```

### Base Station Pi
```bash
sudo apt-get install -y python3-opencv python3-numpy python3-pil python3-pil.imagetk python3-tk
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

## Running

See `RUN_PIPELINE.md` for full step-by-step instructions.

Quick start:
```bash
# 1. Jetson (start first)
python3 jetson_processor.py --port 9001 --return-port 9002

# 2. Base Station Pi
python3 receiver_jetson.py --port 9000 --jetson-host <JETSON_IP>

# 3. Camera Pi
python3 sender.py --host <BASE_STATION_IP> --port 9000
```

### Notable flags

- `--yolo` on `jetson_processor.py` enables YOLOv8 detection (disabled by default)
- `--vlm-interval` on `jetson_processor.py` controls seconds between VLM queries (default 5)
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
