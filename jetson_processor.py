"""
jetson_processor.py — Runs on the Jetson Nano.
Receives JPEG frames via UDP, applies placeholder processing
(green diagonal lines), and sends the result back.

Usage:
    python3 jetson_processor.py --port 9001 --return-port 9002
"""

import argparse
import socket
import struct

import cv2
import numpy as np

MAX_UDP_RECV = 65535
MAX_UDP_PAYLOAD = 65503


def apply_processing(bgr_image):
    """Placeholder: draw green diagonal lines and a label."""
    result = bgr_image.copy()
    h, w = result.shape[:2]
    color = (0, 255, 0)  # green in BGR
    cv2.line(result, (0, 0), (w - 1, h - 1), color, 2)
    cv2.line(result, (w - 1, 0), (0, h - 1), color, 2)
    cv2.putText(result, "JETSON PROCESSED", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return result


def run_processor(port, return_port, reply_host, jpeg_quality):
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    recv_sock.bind(("0.0.0.0", port))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)

    print(f"Jetson processor listening on UDP port {port} ...")
    print(f"Will return processed frames on port {return_port}")

    reply_addr = reply_host
    connected = False

    while True:
        try:
            data, addr = recv_sock.recvfrom(MAX_UDP_RECV)
        except OSError:
            continue

        if not connected:
            print(f"Receiving from {addr}")
            connected = True

        if reply_addr is None:
            reply_addr = addr[0]
            print(f"Reply target set to {reply_addr}:{return_port}")

        # Parse frame
        if len(data) < 4:
            continue
        frame_len = struct.unpack(">I", data[:4])[0]
        jpeg_data = data[4:]
        if len(jpeg_data) != frame_len:
            continue

        # Decode
        bgr = cv2.imdecode(
            np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            continue

        # Process
        processed = apply_processing(bgr)

        # Re-encode as JPEG
        ok, encoded = cv2.imencode(
            ".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        if not ok:
            continue

        jpeg_bytes = encoded.tobytes()

        # If too large, retry at lower quality
        if len(jpeg_bytes) + 4 > MAX_UDP_PAYLOAD:
            ok, encoded = cv2.imencode(
                ".jpg", processed,
                [cv2.IMWRITE_JPEG_QUALITY, max(20, jpeg_quality - 30)])
            if not ok:
                continue
            jpeg_bytes = encoded.tobytes()
            if len(jpeg_bytes) + 4 > MAX_UDP_PAYLOAD:
                continue  # still too big, drop

        # Send back
        header = struct.pack(">I", len(jpeg_bytes))
        try:
            send_sock.sendto(header + jpeg_bytes, (reply_addr, return_port))
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description="Jetson Nano frame processor")
    ap.add_argument("--port", type=int, default=9001,
                    help="UDP port to receive frames (default 9001)")
    ap.add_argument("--return-port", type=int, default=9002,
                    help="UDP port to send processed frames back (default 9002)")
    ap.add_argument("--reply-host", default=None,
                    help="Override reply IP (default: auto-detect from sender)")
    ap.add_argument("--jpeg-quality", type=int, default=85,
                    help="JPEG encode quality (default 85)")
    args = ap.parse_args()

    run_processor(args.port, args.return_port, args.reply_host, args.jpeg_quality)


if __name__ == "__main__":
    main()
