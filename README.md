# RPi Video Streamer

Stream live video from one Raspberry Pi (with camera) to another RPi (base station) over WiFi/TCP.

## Setup

### Both Pis

```bash
sudo apt-get update && sudo apt-get install -y python3-opencv python3-numpy python3-picamera2
```

> The base station doesn't strictly need `python3-picamera2`, but it won't hurt to install it.

## Usage

### 1. Start the Base Station (receiver Pi)

```bash
python3 receiver.py --port 9000
```

This opens a listening socket and waits for the camera Pi to connect.

### 2. Start the Camera Pi (sender Pi)

```bash
python3 sender.py --host <BASE_STATION_IP> --port 9000
```

Replace `<BASE_STATION_IP>` with the base station's IP address. To find it, run `hostname -I` on the base station Pi.

### 3. Quit

Press `q` in the receiver's display window.

## Optional Flags (sender only)

| Flag       | Default | Description       |
|------------|---------|-------------------|
| `--width`  | 640     | Frame width (px)  |
| `--height` | 480     | Frame height (px) |
| `--fps`    | 30      | Target framerate  |

Example at higher resolution:

```bash
python3 sender.py --host 192.168.1.50 --port 9000 --width 1280 --height 720 --fps 24
```

## Finding IP Addresses

On each Pi, run:

```bash
hostname -I
```

## Troubleshooting

- **"Connection refused"** — Make sure the receiver is started first.
- **No display window** — The receiver needs a display (monitor, VNC, or X forwarding).
- **Camera not detected** — Run `rpicam-hello` to verify the camera works.
