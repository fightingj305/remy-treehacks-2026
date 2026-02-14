"""
receiver_deskew.py — Receives MJPEG frames over UDP from a camera Pi
and provides the same tkinter GUI as apriltag_deskew.py: live feed with
tag overlays on the left, deskewed result on the right, with buttons
and keyboard shortcuts to capture, deskew, and save.

Usage:
    python3 receiver_deskew.py --port 9000
    python3 receiver_deskew.py --port 9000 --single-tag 0
    python3 receiver_deskew.py --port 9000 --tags 0,1,2,3
"""

import argparse
import socket
import struct
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

# Display size for each panel — sized to fit 800x480 DSI display
DISPLAY_W = 380
DISPLAY_H = 260


# Max UDP datagram we'll accept
MAX_UDP_RECV = 65535


# ---------------------------------------------------------------------------
# AprilTag detection
# ---------------------------------------------------------------------------

def detect_tags(gray, detector):
    """Run the ArUco/AprilTag detector, return a list of dicts."""
    corners_list, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return []
    results = []
    for i, tag_id in enumerate(ids.flatten()):
        c = corners_list[i][0]
        results.append({
            "id": int(tag_id),
            "center": c.mean(axis=0),
            "corners": c,
        })
    return results


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def order_points(pts):
    """Sort 4 points into top-left, top-right, bottom-right, bottom-left."""
    pts = np.array(pts, dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).flatten()
    return np.array([
        pts[np.argmin(s)],
        pts[np.argmin(d)],
        pts[np.argmax(s)],
        pts[np.argmax(d)],
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Deskew algorithms
# ---------------------------------------------------------------------------

def deskew_four_tags(image, detections, tag_ids, output_size=None):
    """Perspective-correct the region bounded by 4 tags."""
    tag_map = {d["id"]: d for d in detections}
    missing = [t for t in tag_ids if t not in tag_map]
    if missing:
        return None, f"Missing tag(s): {missing}"

    src = np.array([tag_map[t]["center"] for t in tag_ids], dtype=np.float32)

    if output_size:
        w, h = output_size
    else:
        w = int(max(np.linalg.norm(src[1] - src[0]),
                     np.linalg.norm(src[2] - src[3])))
        h = int(max(np.linalg.norm(src[3] - src[0]),
                     np.linalg.norm(src[2] - src[1])))
    if w < 10 or h < 10:
        return None, "Detected region too small"

    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]],
                   dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, M, (w, h)), None


def deskew_single_tag(image, detection):
    """Correct perspective of the full image using one tag's square geometry."""
    ordered = order_points(detection["corners"])
    side = np.mean([np.linalg.norm(ordered[(i + 1) % 4] - ordered[i])
                    for i in range(4)])
    cx, cy = ordered.mean(axis=0)
    half = side / 2.0
    dst = np.array([
        [cx - half, cy - half],
        [cx + half, cy - half],
        [cx + half, cy + half],
        [cx - half, cy + half],
    ], dtype=np.float32)
    M = cv2.getPerspectiveTransform(ordered, dst)
    h, w = image.shape[:2]
    return cv2.warpPerspective(image, M, (w, h)), None


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_overlay(image, detections):
    """Draw detected tag outlines and IDs onto the image."""
    vis = image.copy()
    for det in detections:
        pts = det["corners"].astype(np.int32)
        cv2.polylines(vis, [pts], True, (0, 255, 0), 3)
        cx, cy = int(det["center"][0]), int(det["center"][1])
        cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(vis, str(det["id"]), (cx - 12, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    return vis


def rgb_to_photoimage(rgb_array, max_w, max_h):
    """Convert an RGB numpy array to a tkinter PhotoImage, fit within bounds."""
    h, w = rgb_array.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    if scale < 1.0:
        resized = cv2.resize(rgb_array, (new_w, new_h),
                             interpolation=cv2.INTER_AREA)
    else:
        resized = rgb_array
    pil_img = Image.fromarray(resized)
    return ImageTk.PhotoImage(pil_img), new_w, new_h


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class ReceiverDeskewApp:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.root.title("Receiver — AprilTag Deskew")
        self.root.geometry("800x480")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.tag_ids = [int(x) for x in args.tags.split(",")]
        self.single_tag_id = args.single_tag
        self.needed_ids = ([self.single_tag_id] if self.single_tag_id is not None
                           else self.tag_ids)
        self.output_size = None
        if args.output_size:
            parts = args.output_size.split("x")
            self.output_size = (int(parts[0]), int(parts[1]))

        self.running = True
        self.last_frame = None        # latest RGB frame from network
        self.last_detections = []
        self.deskewed_rgb = None
        self.save_count = 0
        self.connected = False

        # Lock protects last_frame / last_detections written by net thread
        self._frame_lock = threading.Lock()

        self._setup_detector()
        self._build_gui()
        self._start_network_thread()
        self._update_feed()

    # -- Initialisation --

    def _setup_detector(self):
        dictionary = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, self.args.family))
        params = cv2.aruco.DetectorParameters()
        # Tune for small tags in a low-res MJPEG stream
        params.adaptiveThreshWinSizeMin = 3
        params.adaptiveThreshWinSizeMax = 30
        params.adaptiveThreshWinSizeStep = 3
        params.minMarkerPerimeterRate = 0.01   # default 0.03 — accept much smaller tags
        params.maxMarkerPerimeterRate = 4.0
        params.polygonalApproxAccuracyRate = 0.05  # more lenient corner fitting
        params.minCornerDistanceRate = 0.01
        params.minDistanceToBorder = 1             # detect tags near frame edges
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(dictionary, params)

    # -- Network receiver thread --

    def _start_network_thread(self):
        self._net_thread = threading.Thread(target=self._network_loop,
                                            daemon=True)
        self._net_thread.start()

    def _network_loop(self):
        """Runs in a background thread: receives UDP datagrams with JPEG frames."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        sock.bind(("0.0.0.0", self.args.port))
        print(f"Listening on UDP port {self.args.port} ...")

        while self.running:
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(MAX_UDP_RECV)
            except socket.timeout:
                continue
            except OSError:
                continue

            if not self.connected:
                print(f"Receiving from {addr}")
                self.connected = True

            # Need at least 4-byte header
            if len(data) < 4:
                continue
            frame_len = struct.unpack(">I", data[:4])[0]
            jpeg_data = data[4:]
            if len(jpeg_data) != frame_len:
                continue  # truncated datagram

            # Decode JPEG → BGR, then convert to RGB for tkinter
            bgr = cv2.imdecode(
                np.frombuffer(jpeg_data, dtype=np.uint8),
                cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            # Detect tags (on grayscale)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            detections = detect_tags(gray, self.detector)

            with self._frame_lock:
                self.last_frame = rgb
                self.last_detections = detections

        sock.close()

    # -- GUI layout (mirrors apriltag_deskew.py) --

    def _build_gui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("sans-serif", 8))
        style.configure("Header.TLabel", font=("sans-serif", 9, "bold"),
                         foreground="#89b4fa")
        style.configure("Status.TLabel", font=("sans-serif", 9),
                         foreground="#a6e3a1")
        style.configure("Warn.TLabel", font=("sans-serif", 9),
                         foreground="#fab387")
        style.configure("TButton", font=("sans-serif", 8, "bold"),
                         padding=3)

        # -- Top: two image panels side by side --
        panels = ttk.Frame(self.root)
        panels.pack(padx=4, pady=(4, 2), fill="both", expand=True)

        # Left panel: live feed
        left = ttk.Frame(panels)
        left.pack(side="left", padx=(0, 4), fill="both", expand=True)
        ttk.Label(left, text="Live Camera Feed",
                  style="Header.TLabel").pack(anchor="w")
        self.feed_canvas = tk.Canvas(left, width=DISPLAY_W, height=DISPLAY_H,
                                     bg="#181825", highlightthickness=0)
        self.feed_canvas.pack(fill="both", expand=True)
        self._feed_photo = None

        # Right panel: deskewed result
        right = ttk.Frame(panels)
        right.pack(side="left", padx=(4, 0), fill="both", expand=True)
        ttk.Label(right, text="Deskewed Result",
                  style="Header.TLabel").pack(anchor="w")
        self.result_canvas = tk.Canvas(right, width=DISPLAY_W, height=DISPLAY_H,
                                       bg="#181825", highlightthickness=0)
        self.result_canvas.pack(fill="both", expand=True)
        self._result_photo = None

        # -- Middle: status bar --
        status_frame = ttk.Frame(self.root)
        status_frame.pack(padx=4, fill="x")
        self.status_var = tk.StringVar(
            value=f"Waiting for camera on port {self.args.port} ...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                      style="Warn.TLabel")
        self.status_label.pack(side="left")

        # -- Bottom: controls --
        controls = ttk.Frame(self.root)
        controls.pack(padx=4, pady=(2, 4), fill="x")

        ttk.Button(controls, text="Detect & Deskew",
                   command=self.do_deskew).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Save Deskewed",
                   command=self.save_deskewed).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Save Raw",
                   command=self.save_raw).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Quit",
                   command=self.quit).pack(side="left", padx=(0, 6))

        # Mode selector
        mode_frame = ttk.Frame(controls)
        mode_frame.pack(side="right")
        self.mode_var = tk.StringVar(
            value="single" if self.single_tag_id is not None else "four")
        ttk.Radiobutton(mode_frame, text="4-Tag", variable=self.mode_var,
                         value="four", command=self._mode_changed).pack(side="left")
        ttk.Radiobutton(mode_frame, text="Single-Tag", variable=self.mode_var,
                         value="single", command=self._mode_changed).pack(
                             side="left", padx=(6, 0))
        ttk.Label(mode_frame, text="  Tag ID:").pack(side="left")
        self.single_id_var = tk.StringVar(
            value=str(self.single_tag_id if self.single_tag_id is not None else 0))
        self.single_id_spin = tk.Spinbox(
            mode_frame, from_=0, to=586, width=4, font=("sans-serif", 8),
            textvariable=self.single_id_var, command=self._mode_changed)
        self.single_id_spin.pack(side="left", padx=(2, 0))

        # Keyboard shortcuts
        self.root.bind("<space>", lambda e: self.do_deskew())
        self.root.bind("s", lambda e: self.save_deskewed())
        self.root.bind("r", lambda e: self.save_raw())
        self.root.bind("q", lambda e: self.quit())
        self.root.bind("<Escape>", lambda e: self.quit())

    def _mode_changed(self):
        if self.mode_var.get() == "single":
            try:
                self.single_tag_id = int(self.single_id_var.get())
            except ValueError:
                self.single_tag_id = 0
            self.needed_ids = [self.single_tag_id]
        else:
            self.single_tag_id = None
            self.needed_ids = self.tag_ids

    # -- Feed update loop (runs on tkinter main thread) --

    def _update_feed(self):
        if not self.running:
            return

        with self._frame_lock:
            frame = self.last_frame
            detections = list(self.last_detections)

        if frame is not None:
            # Draw overlay on a copy
            vis = draw_overlay(frame, detections)

            # Update status
            fh, fw = frame.shape[:2]
            res_str = f"[{fw}x{fh}]"
            found_ids = sorted([d["id"] for d in detections])
            ready = all(t in found_ids for t in self.needed_ids)
            if ready:
                self.status_var.set(
                    f"{res_str}  Tags: {found_ids}  --  "
                    f"Ready to deskew (Space / click button)")
                self.status_label.configure(style="Status.TLabel")
            else:
                missing = [t for t in self.needed_ids if t not in found_ids]
                self.status_var.set(
                    f"{res_str}  Tags: {found_ids}  --  Missing: {missing}")
                self.status_label.configure(style="Warn.TLabel")

            # Render to left canvas
            cw = self.feed_canvas.winfo_width()
            ch = self.feed_canvas.winfo_height()
            if cw < 2 or ch < 2:
                cw, ch = DISPLAY_W, DISPLAY_H
            photo, pw, ph = rgb_to_photoimage(vis, cw, ch)
            self._feed_photo = photo  # prevent GC
            self.feed_canvas.delete("all")
            self.feed_canvas.create_image(cw // 2, ch // 2, image=photo)

        elif not self.connected:
            self.status_var.set(
                f"Waiting for camera on port {self.args.port} ...")
            self.status_label.configure(style="Warn.TLabel")

        self.root.after(50, self._update_feed)  # ~20 fps

    # -- Actions --

    def do_deskew(self):
        with self._frame_lock:
            frame = self.last_frame
            detections = list(self.last_detections)

        if frame is None:
            return

        if self.single_tag_id is not None:
            det = next((d for d in detections
                        if d["id"] == self.single_tag_id), None)
            if det is None:
                self.status_var.set(
                    f"Cannot deskew: tag {self.single_tag_id} not found")
                self.status_label.configure(style="Warn.TLabel")
                return
            result, err = deskew_single_tag(frame, det)
        else:
            result, err = deskew_four_tags(
                frame, detections, self.tag_ids, self.output_size)

        if err:
            self.status_var.set(f"Deskew failed: {err}")
            self.status_label.configure(style="Warn.TLabel")
            return

        if self.output_size:
            result = cv2.resize(result, self.output_size)

        self.deskewed_rgb = result
        self._show_result(result)
        self.status_var.set("Deskewed! Press 's' or click Save.")
        self.status_label.configure(style="Status.TLabel")

    def _show_result(self, rgb_array):
        cw = self.result_canvas.winfo_width()
        ch = self.result_canvas.winfo_height()
        if cw < 2 or ch < 2:
            cw, ch = DISPLAY_W, DISPLAY_H
        photo, pw, ph = rgb_to_photoimage(rgb_array, cw, ch)
        self._result_photo = photo
        self.result_canvas.delete("all")
        self.result_canvas.create_image(cw // 2, ch // 2, image=photo)

    def save_deskewed(self):
        if self.deskewed_rgb is None:
            self.status_var.set("Nothing to save -- run Detect & Deskew first")
            self.status_label.configure(style="Warn.TLabel")
            return
        self.save_count += 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"deskewed_{ts}.jpg"
        cv2.imwrite(fname, cv2.cvtColor(self.deskewed_rgb, cv2.COLOR_RGB2BGR))
        self.status_var.set(f"Saved: {fname}")
        self.status_label.configure(style="Status.TLabel")

    def save_raw(self):
        with self._frame_lock:
            frame = self.last_frame

        if frame is None:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"raw_{ts}.jpg"
        cv2.imwrite(fname, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        self.status_var.set(f"Saved raw: {fname}")
        self.status_label.configure(style="Status.TLabel")

    def quit(self):
        self.running = False
        self.root.destroy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Receive MJPEG stream and deskew with AprilTags (GUI)")

    ap.add_argument("--port", type=int, default=9000,
                    help="Port (default 9000)")
    ap.add_argument("--tags", default="0,1,2,3",
                    help="4 tag IDs as TL,TR,BR,BL (default: 0,1,2,3)")
    ap.add_argument("--single-tag", type=int, default=None, metavar="ID",
                    help="Use a single tag for deskewing instead of four")
    ap.add_argument("--family", default="DICT_APRILTAG_36h11",
                    choices=["DICT_APRILTAG_36h11", "DICT_APRILTAG_36h10",
                             "DICT_APRILTAG_25h9", "DICT_APRILTAG_16h5"],
                    help="Tag family (default: DICT_APRILTAG_36h11)")
    ap.add_argument("--output-size", default=None, metavar="WxH",
                    help="Force output size, e.g. 1920x1080")
    args = ap.parse_args()

    tag_ids = [int(x) for x in args.tags.split(",")]
    if len(tag_ids) != 4 and args.single_tag is None:
        ap.error("--tags must specify exactly 4 comma-separated IDs")

    root = tk.Tk()
    ReceiverDeskewApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
