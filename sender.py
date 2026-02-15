"""
sender.py — Runs on the Camera RPi.
Captures video from a USB webcam (e.g. Logitech Brio) and streams
MJPEG frames over UDP to the base station.

Usage:
    python3 sender.py --host <BASE_STATION_IP> --port 9000
"""

import argparse
import socket
import struct
import time

import cv2

# Max safe UDP payload (65535 - 20 IP header - 8 UDP header - 4 our header)
MAX_UDP_PAYLOAD = 65503


def start_streaming(host, port, width, height, fps):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    dest = (host, port)

    print(f"Streaming UDP to {host}:{port} ({width}x{height} @ {fps}fps) ...")

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
    frame_interval = 1.0 / fps

    try:
        while True:
            t0 = time.monotonic()
            ret, frame = cap.read()
            if not ret:
                continue

            ok, jpeg = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue

            data = jpeg.tobytes()
            if len(data) > MAX_UDP_PAYLOAD:
                continue  # skip oversized frames

            header = struct.pack(">I", len(data))
            try:
                sock.sendto(header + data, dest)
            except OSError:
                pass

            elapsed = time.monotonic() - t0
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    finally:
        cap.release()
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="RPi Camera Streamer (sender)")
    parser.add_argument("--host", required=True, help="Base station IP address")
    parser.add_argument("--port", type=int, default=9000, help="Port (default 9000)")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--fps", type=int, default=30, help="Framerate")
    args = parser.parse_args()

    start_streaming(args.host, args.port, args.width, args.height, args.fps)


if __name__ == "__main__":
    main()
