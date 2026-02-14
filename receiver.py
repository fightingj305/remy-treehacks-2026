"""
receiver.py — Runs on the Base Station RPi.
Listens for incoming UDP datagrams from the camera Pi
and displays the received MJPEG stream.

Usage:
    python3 receiver.py --port 9000
"""

import argparse
import socket
import struct

import cv2
import numpy as np

MAX_UDP_RECV = 65535


def start_receiver(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    sock.bind(("0.0.0.0", port))
    print(f"Base station listening on UDP port {port} ...")

    # Set up fullscreen window for DSI display
    window_name = "Base Station - Live Feed"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    connected = False
    while True:
        try:
            data, addr = sock.recvfrom(MAX_UDP_RECV)
        except OSError:
            continue

        if not connected:
            print(f"Receiving from {addr}")
            connected = True

        if len(data) < 4:
            continue
        frame_len = struct.unpack(">I", data[:4])[0]
        jpeg_data = data[4:]
        if len(jpeg_data) != frame_len:
            continue

        frame = cv2.imdecode(
            np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR
        )
        if frame is not None:
            cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Quitting ...")
            sock.close()
            cv2.destroyAllWindows()
            return


def main():
    parser = argparse.ArgumentParser(description="RPi Base Station (receiver)")
    parser.add_argument("--port", type=int, default=9000, help="Port (default 9000)")
    args = parser.parse_args()

    start_receiver(args.port)


if __name__ == "__main__":
    main()
