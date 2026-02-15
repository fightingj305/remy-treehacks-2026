"""
jetson_processor.py — Runs on the Jetson Orin Nano.
Receives JPEG frames via UDP, optionally runs YOLOv8n object detection
(TensorRT-accelerated), and sends the annotated result back.
Periodically sends frames to a local Ollama VLM for scene analysis.

Usage:
    python3 jetson_processor.py --port 9001 --return-port 9002
    python3 jetson_processor.py --yolo --model yolov8n.pt --conf 0.25
"""

import argparse
import base64
import json
import logging
import os
import socket
import struct
import threading
import time
import urllib.request
from datetime import datetime
from queue import Queue, Full

import cv2
import numpy as np

MAX_UDP_RECV = 65535
MAX_UDP_PAYLOAD = 65503

# Ollama VLM settings
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3-vl:2b"
OLLAMA_PROMPT = (
    "Think concisely, but your output can be long and very descriptive. "
    "Analyze this image and respond with ALL three of the following sections:\n\n"
    "**Action:** Describe in vivid detail every action, movement, gesture, and activity "
    "happening in the scene. Include body language, interactions between people or objects, "
    "direction of motion, and any implied intent behind the actions.\n\n"
    "**Tools:** List and describe every tool, instrument, device, utensil, equipment, "
    "appliance, or functional object visible. Include their condition, position, how they "
    "are being used or held, and any brand or type identifiers you can discern.\n\n"
    "**Description of food:** Describe all food and beverages visible in thorough detail. "
    "Include colors, textures, apparent temperatures, cooking methods, portion sizes, "
    "plating style, garnishes, containers, and any identifiable ingredients or dishes. "
    "If no food is visible, state 'No food visible' and describe what occupies that space instead."
)
VLM_INTERVAL_SEC = 5
VLM_QUEUE_MAXSIZE = 3
VLM_UDP_PORT = 9003

# 20-color palette (BGR) for visually distinct bounding boxes per class
BOX_COLORS = [
    (255, 56, 56),   (255, 157, 151), (255, 112, 31),  (255, 178, 29),
    (207, 210, 49),  (72, 249, 10),   (146, 204, 23),  (61, 219, 134),
    (26, 147, 52),   (0, 212, 187),   (44, 153, 168),  (0, 194, 255),
    (52, 69, 147),   (100, 115, 255), (0, 24, 236),    (132, 56, 255),
    (82, 0, 133),    (203, 56, 255),  (255, 149, 200), (255, 55, 199),
]


def load_model(model_path, conf_threshold):
    """Load YOLOv8 model, exporting to TensorRT FP16 engine if needed."""
    from ultralytics import YOLO

    stem = os.path.splitext(model_path)[0]
    engine_path = stem + ".engine"
    onnx_path = stem + ".onnx"

    if model_path.endswith(".engine"):
        engine_path = model_path
    elif os.path.isfile(engine_path):
        print(f"Found existing TensorRT engine: {engine_path}")
    else:
        # Need to build engine — check for existing ONNX first
        if os.path.isfile(onnx_path):
            print(f"Found existing ONNX: {onnx_path}, exporting to TensorRT FP16...")
            onnx_model = YOLO(onnx_path, task="detect")
            onnx_model.export(format="engine", half=True)
        else:
            print(f"Exporting {model_path} to TensorRT FP16 (this takes several minutes on first run)...")
            base_model = YOLO(model_path)
            base_model.export(format="engine", half=True)

    model = YOLO(engine_path, task="detect")

    model.conf = conf_threshold

    # Warm-up inference to pre-allocate GPU memory
    print("Running warm-up inference...")
    warmup_img = np.zeros((640, 640, 3), dtype=np.uint8)
    model.predict(warmup_img, verbose=False)
    print("Model ready.")

    return model


def apply_processing(bgr_image, model):
    """Run YOLOv8 detection and draw bounding boxes with class labels.
    If model is None, return the image unmodified (passthrough)."""
    if model is None:
        return bgr_image

    results = model.predict(bgr_image, verbose=False)
    annotated = bgr_image.copy()

    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0].int().tolist()
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        color = BOX_COLORS[cls_id % len(BOX_COLORS)]

        # Bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Label background + text
        (tw, th), _ = cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, class_name, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return annotated


# ---------------------------------------------------------------------------
# VLM (Ollama) helpers
# ---------------------------------------------------------------------------

def query_ollama(jpeg_bytes):
    """Send a JPEG frame to the local Ollama VLM and return the response text."""
    b64_img = base64.b64encode(jpeg_bytes).decode("ascii")
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": OLLAMA_PROMPT,
                "images": [b64_img],
            }
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        return body["message"]["content"].strip()
    except Exception as exc:
        return f"[ERROR] {exc}"


def setup_vlm_logger():
    """Create a file logger under vlm_logs/ for this run."""
    os.makedirs("vlm_logs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"vlm_logs/vlm_analysis_{ts}.log"

    logger = logging.getLogger("vlm_analysis")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    logger.addHandler(handler)

    print(f"VLM analysis log: {log_path}")
    return logger


def vlm_analysis_thread(frame_queue, reply_addr_holder, vlm_port, logger,
                        running_event):
    """Daemon thread: pull JPEG from queue, query Ollama, log, send via UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while running_event.is_set():
        try:
            jpeg_data = frame_queue.get(timeout=1.0)
        except Exception:
            continue

        ts = datetime.now().strftime("%H:%M:%S")
        result = query_ollama(jpeg_data)

        msg = f"[VLM {ts}] {result}"
        logger.info(result)
        print(msg)

        # Send to receiver if we know the address
        addr = reply_addr_holder[0]
        if addr is not None:
            try:
                sock.sendto(msg.encode("utf-8"), (addr, vlm_port))
            except OSError:
                pass

    sock.close()


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------

def run_processor(port, return_port, reply_host, jpeg_quality, model,
                  vlm_port, vlm_interval):
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    recv_sock.bind(("0.0.0.0", port))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)

    print(f"Jetson processor listening on UDP port {port} ...")
    print(f"Will return processed frames on port {return_port}")

    # VLM setup
    vlm_queue = Queue(maxsize=VLM_QUEUE_MAXSIZE)
    vlm_logger = setup_vlm_logger()
    running_event = threading.Event()
    running_event.set()
    reply_addr_holder = [reply_host]  # mutable list shared with VLM thread

    vlm_thread = threading.Thread(
        target=vlm_analysis_thread,
        args=(vlm_queue, reply_addr_holder, vlm_port, vlm_logger,
              running_event),
        daemon=True,
    )
    vlm_thread.start()

    reply_addr = reply_host
    connected = False
    last_vlm_time = 0.0

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
            reply_addr_holder[0] = reply_addr
            print(f"Reply target set to {reply_addr}:{return_port}")

        # Parse frame
        if len(data) < 4:
            continue
        frame_len = struct.unpack(">I", data[:4])[0]
        jpeg_data = data[4:]
        if len(jpeg_data) != frame_len:
            continue

        # Feed VLM at configured interval (original un-annotated JPEG)
        now = time.monotonic()
        if now - last_vlm_time >= vlm_interval:
            last_vlm_time = now
            try:
                vlm_queue.put_nowait(jpeg_data)
            except Full:
                pass  # queue full, silently drop

        # Decode
        bgr = cv2.imdecode(
            np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            continue

        # Process
        processed = apply_processing(bgr, model)

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
    ap = argparse.ArgumentParser(description="Jetson Orin Nano frame processor (YOLOv8 TensorRT)")
    ap.add_argument("--port", type=int, default=9001,
                    help="UDP port to receive frames (default 9001)")
    ap.add_argument("--return-port", type=int, default=9002,
                    help="UDP port to send processed frames back (default 9002)")
    ap.add_argument("--reply-host", default=None,
                    help="Override reply IP (default: auto-detect from sender)")
    ap.add_argument("--jpeg-quality", type=int, default=85,
                    help="JPEG encode quality (default 85)")
    ap.add_argument("--yolo", action="store_true", default=False,
                    help="Enable YOLOv8 detection (default: disabled)")
    ap.add_argument("--model", default="yolov8n.pt",
                    help="Path to YOLOv8 .pt or .engine file (default yolov8n.pt)")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection confidence threshold (default 0.25)")
    ap.add_argument("--vlm-port", type=int, default=VLM_UDP_PORT,
                    help=f"UDP port for VLM analysis text (default {VLM_UDP_PORT})")
    ap.add_argument("--vlm-interval", type=float, default=VLM_INTERVAL_SEC,
                    help=f"Seconds between VLM queries (default {VLM_INTERVAL_SEC})")
    args = ap.parse_args()

    model = None
    if args.yolo:
        model = load_model(args.model, args.conf)
    else:
        print("YOLO disabled (passthrough mode). Use --yolo to enable detection.")

    run_processor(args.port, args.return_port, args.reply_host,
                  args.jpeg_quality, model, args.vlm_port, args.vlm_interval)


if __name__ == "__main__":
    main()
