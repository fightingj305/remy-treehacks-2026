# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPi Video Streamer — streams live MJPEG video from a Raspberry Pi with a camera (`sender.py`) to a base station RPi (`receiver.py`) over TCP. Built for TreeHacks 2026.

## Architecture

Two standalone Python scripts communicating over a raw TCP socket:

- **sender.py** (Camera Pi): Uses `picamera2` to capture video, encodes as MJPEG, sends each JPEG frame over TCP with a 4-byte big-endian length header. Auto-reconnects on connection loss. Custom `SocketOutput` subclass of `picamera2.outputs.FileOutput` handles frame transmission.
- **receiver.py** (Base Station Pi): Listens on a TCP socket, reads length-prefixed JPEG frames, decodes with OpenCV (`cv2.imdecode`), and displays via `cv2.imshow`. Waits for reconnect if sender disconnects.

Wire protocol: `[4-byte big-endian uint32 frame length][JPEG frame bytes]` per frame.

## Dependencies

System packages (installed via apt, not pip):
```bash
sudo apt-get install -y python3-opencv python3-numpy python3-picamera2
```

- `picamera2` — only needed on the sender (camera Pi)
- `opencv-python` (`cv2`) and `numpy` — needed on the receiver (base station)

## Running

```bash
# Base station (start first)
python3 receiver.py --port 9000

# Camera Pi
python3 sender.py --host <BASE_STATION_IP> --port 9000

# Optional sender flags: --width 640 --height 480 --fps 30
```

Press `q` in the receiver's display window to quit.

## Platform

Target hardware is Raspberry Pi (ARM/Linux). The sender requires a connected RPi camera module. The receiver requires a display (monitor, VNC, or X forwarding) for the OpenCV window.
