"""
sender.py — Runs on the Camera RPi.
Captures video from the RPi camera and streams MJPEG frames
over UDP to the base station.

Usage:
    python3 sender.py --host <BASE_STATION_IP> --port 9000
"""

import argparse
import socket
import struct
import time

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput


# Max safe UDP payload (65535 - 20 IP header - 8 UDP header - 4 our header)
MAX_UDP_PAYLOAD = 65503


class UDPOutput(FileOutput):
    """Custom output that sends each JPEG frame as a UDP datagram,
    prefixed with a 4-byte big-endian length header."""

    def __init__(self, sock, dest):
        super().__init__(sock)
        self.sock = sock
        self.dest = dest

    def outputframe(self, frame, keyframe=True, timestamp=None):
        if len(frame) > MAX_UDP_PAYLOAD:
            return  # skip frames too large for a single datagram
        try:
            header = struct.pack(">I", len(frame))
            self.sock.sendto(header + frame, self.dest)
        except OSError:
            pass  # drop frame silently on any send error


def start_streaming(host, port, width, height, fps):
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (width, height), "format": "RGB888"},
        controls={"FrameRate": fps},
    )
    picam2.configure(video_config)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    dest = (host, port)

    print(f"Streaming UDP to {host}:{port} ({width}x{height} @ {fps}fps) ...")

    while True:
        try:
            encoder = MJPEGEncoder()
            output = UDPOutput(sock, dest)
            picam2.start_recording(encoder, output)

            while True:
                time.sleep(1)

        except Exception as e:
            print(f"Error ({e}). Restarting encoder ...")
            try:
                picam2.stop_recording()
            except Exception:
                pass
            time.sleep(1)


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
