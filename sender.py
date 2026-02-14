"""
sender.py — Runs on the Camera RPi.
Captures video from the RPi camera and streams MJPEG frames
over TCP to the base station.

Usage:
    python3 sender.py --host <BASE_STATION_IP> --port 9000
"""

import argparse
import io
import socket
import struct
import time

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput


class SocketOutput(FileOutput):
    """Custom output that sends each JPEG frame over a TCP socket,
    prefixed with a 4-byte big-endian length header."""

    def __init__(self, conn):
        super().__init__(conn)
        self.conn = conn

    def outputframe(self, frame, keyframe=True, timestamp=None):
        try:
            header = struct.pack(">I", len(frame))
            self.conn.sendall(header + frame)
        except (BrokenPipeError, ConnectionResetError):
            raise


def start_streaming(host, port, width, height, fps):
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (width, height), "format": "RGB888"},
        controls={"FrameRate": fps},
    )
    picam2.configure(video_config)

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connecting to base station at {host}:{port} ...")
        try:
            sock.connect((host, port))
        except ConnectionRefusedError:
            print("  Base station not ready, retrying in 2s ...")
            sock.close()
            time.sleep(2)
            continue

        print("Connected! Streaming ...")
        try:
            encoder = MJPEGEncoder()
            output = SocketOutput(sock)
            picam2.start_recording(encoder, output)

            # Keep streaming until the connection drops
            while True:
                time.sleep(1)

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"Connection lost ({e}). Reconnecting ...")
        finally:
            try:
                picam2.stop_recording()
            except Exception:
                pass
            sock.close()
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
