# Running the Full Pipeline

This guide walks through starting the complete Camera Pi → Base Station Pi → Jetson Orin Nano pipeline.

## Network Setup

All three devices must be on the same network (or have direct routes to each other). You will need to know:

- **Camera Pi IP** — the RPi with the camera module
- **Base Station Pi IP** — the RPi with the display (runs the GUI)
- **Jetson IP** — the Jetson Orin Nano (default `192.168.55.1` if using USB device mode)

### Port summary

| Port | From → To | Content |
|------|-----------|---------|
| 9000 | Camera Pi → Base Station | Raw JPEG frames |
| 9001 | Base Station → Jetson | Forwarded JPEG frames |
| 9002 | Jetson → Base Station | Annotated JPEG frames |
| 9003 | Jetson → Base Station | VLM analysis text |

Make sure these ports are not blocked by any firewalls on the devices.

---

## Prerequisites

### Camera Pi

```bash
sudo apt-get install -y python3-picamera2
```

Verify the camera is detected:

```bash
libcamera-hello --list-cameras
```

### Base Station Pi

```bash
sudo apt-get install -y python3-opencv python3-numpy python3-pil python3-pil.imagetk python3-tk
```

### Jetson Orin Nano

```bash
# Core dependencies
sudo apt-get install -y python3-opencv python3-numpy

# Ollama (required for VLM analysis)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3-vl:2b

# YOLOv8 (only if you plan to use --yolo)
pip3 install ultralytics
```

---

## Step-by-step startup

Start the devices in this order: **Jetson → Base Station → Camera Pi**.

### Step 1: Start Ollama on the Jetson

SSH into the Jetson and make sure Ollama is running:

```bash
# Check if Ollama is already running
ollama list

# If not running, start it
ollama serve &
```

Confirm the VLM model is available:

```bash
ollama list
# Should show: qwen3-vl:2b
```

### Step 2: Start the Jetson processor

On the Jetson, from the repo directory:

```bash
# VLM-only mode (default — no YOLO, just passthrough + VLM analysis)
python3 jetson_processor.py

# With YOLOv8 object detection enabled
python3 jetson_processor.py --yolo

# With custom settings
python3 jetson_processor.py --yolo --vlm-interval 10 --conf 0.3
```

You should see:

```
YOLO disabled (passthrough mode). Use --yolo to enable detection.
Jetson processor listening on UDP port 9001 ...
Will return processed frames on port 9002
VLM analysis log: vlm_logs/vlm_analysis_YYYYMMDD_HHMMSS.log
```

**Jetson processor flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | 9001 | UDP port to receive frames |
| `--return-port` | 9002 | UDP port to send processed frames back |
| `--reply-host` | auto-detect | Override reply IP address |
| `--jpeg-quality` | 85 | JPEG encode quality for output |
| `--yolo` | off | Enable YOLOv8 TensorRT detection |
| `--model` | yolov8n.pt | YOLOv8 model path (only with `--yolo`) |
| `--conf` | 0.25 | Detection confidence threshold (only with `--yolo`) |
| `--vlm-port` | 9003 | UDP port for VLM analysis text output |
| `--vlm-interval` | 5.0 | Seconds between VLM queries |

### Step 3: Start the Base Station receiver

On the Base Station Pi, from the repo directory:

```bash
python3 receiver_jetson.py --jetson-host <JETSON_IP>

# Example with Jetson on USB device mode
python3 receiver_jetson.py --jetson-host 192.168.55.1
```

You should see:

```
Listening for camera on UDP port 9000 ...
Listening for Jetson return on UDP port 9002 ...
Listening for VLM analysis on UDP port 9003 ...
```

A Tkinter window will open showing:
- **Left panel**: Original camera feed
- **Right panel**: Jetson-processed feed (with YOLO boxes if enabled)
- **VLM Analysis Log**: Rolling text log of scene descriptions
- **Status bar**: FPS counters and connection status
- **Buttons**: Save Raw (`r`), Save Processed (`p`), Quit (`q`/`Escape`)

**Base Station receiver flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | 9000 | UDP port to receive camera frames |
| `--jetson-host` | 192.168.55.1 | Jetson IP address |
| `--jetson-port` | 9001 | UDP port to forward frames to Jetson |
| `--return-port` | 9002 | UDP port for processed frames from Jetson |
| `--vlm-port` | 9003 | UDP port for VLM analysis text from Jetson |

### Step 4: Start the Camera Pi sender

On the Camera Pi, from the repo directory:

```bash
python3 sender.py --host <BASE_STATION_IP>

# With custom resolution and framerate
python3 sender.py --host <BASE_STATION_IP> --width 640 --height 480 --fps 30
```

**Camera sender flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | (required) | Base Station IP address |
| `--port` | 9000 | UDP port to send frames to |
| `--width` | 640 | Frame width in pixels |
| `--height` | 480 | Frame height in pixels |
| `--fps` | 30 | Capture framerate |

---

## What to expect

Once all three are running:

1. **Immediately**: The left panel shows the live camera feed. Status bar shows camera FPS.
2. **Within 1-2 frames**: The right panel shows the Jetson-processed feed (passthrough or YOLO-annotated). Status bar shows both FPS counters.
3. **After ~5 seconds**: The first VLM analysis appears in the log widget and prints on the Jetson console. Each entry has a `[VLM HH:MM:SS]` timestamp.
4. **Every ~5 seconds**: New VLM entries appear with scene descriptions containing **Action**, **Tools**, and **Description of food** sections.

VLM analysis results are also saved to `vlm_logs/vlm_analysis_*.log` on the Jetson for later review.

---

## Troubleshooting

### No video on base station
- Verify Camera Pi can reach Base Station: `ping <BASE_STATION_IP>` from Camera Pi
- Check port 9000 is not in use: `ss -ulnp | grep 9000`

### No processed frames (right panel stays black)
- Verify Base Station can reach Jetson: `ping <JETSON_IP>` from Base Station
- Check Jetson processor is running and shows "Receiving from ..."
- Check ports 9001/9002 are not blocked

### VLM log stays empty
- Verify Ollama is running: `curl http://<JETSON_IP>:11434/api/tags`
- Check `vlm_logs/` on the Jetson for `[ERROR]` entries in the log file
- Increase timeout if Ollama is slow on first query (model loading)

### YOLO is slow or fails to load
- First run exports to TensorRT — this takes several minutes on the Jetson
- Subsequent runs use the cached `.engine` file and start quickly
- Make sure `ultralytics` is installed: `pip3 install ultralytics`

### Low FPS
- Reduce sender resolution: `--width 320 --height 240`
- Lower JPEG quality: `--jpeg-quality 60` on the Jetson
- VLM analysis does NOT affect FPS — it runs in a separate thread
