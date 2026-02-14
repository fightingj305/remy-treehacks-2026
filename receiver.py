"""
receiver.py — Runs on the Base Station RPi.
Listens for an incoming TCP connection from the camera Pi
and displays the received MJPEG stream.

Usage:
    python3 receiver.py --port 9000
"""

import argparse
import socket
import struct

import cv2
import numpy as np


def recv_exact(conn, n):
    """Receive exactly n bytes from the socket."""
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Sender disconnected")
        buf.extend(chunk)
    return bytes(buf)


def start_receiver(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(1)
    print(f"Base station listening on port {port} ...")

    while True:
        conn, addr = server.accept()
        print(f"Camera connected from {addr}")

        try:
            while True:
                # Read 4-byte length header
                raw_len = recv_exact(conn, 4)
                frame_len = struct.unpack(">I", raw_len)[0]

                # Read the JPEG frame
                jpeg_data = recv_exact(conn, frame_len)

                # Decode and display
                frame = cv2.imdecode(
                    np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if frame is not None:
                    cv2.imshow("Base Station - Live Feed", frame)

                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Quitting ...")
                    conn.close()
                    server.close()
                    cv2.destroyAllWindows()
                    return

        except ConnectionError:
            print("Camera disconnected. Waiting for reconnect ...")
            conn.close()

    server.close()


def main():
    parser = argparse.ArgumentParser(description="RPi Base Station (receiver)")
    parser.add_argument("--port", type=int, default=9000, help="Port (default 9000)")
    args = parser.parse_args()

    start_receiver(args.port)


if __name__ == "__main__":
    main()
