#!/usr/bin/env python3
"""
AprilTag-based perspective correction for Raspberry Pi Camera.

Detects AprilTags in the camera feed and uses their known geometry to
compute a perspective transform that deskews (rectifies) the image.

Two modes of operation:
  4-tag mode:  Place tags at corners of the region you want to capture.
               The area bounded by the 4 tag centers is warped to a rectangle.
  1-tag mode:  A single tag's square geometry defines the plane orientation.
               The full image is corrected so that plane appears head-on.

Setup:
  sudo apt install python3-opencv python3-pil.imagetk
  python3 apriltag_deskew.py --generate-tags   # print these out

Usage:
  python3 apriltag_deskew.py                   # GUI with live preview
  python3 apriltag_deskew.py --capture          # headless single shot
  python3 apriltag_deskew.py --single-tag 0     # one-tag mode
"""

import argparse
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import cv2
import numpy as np
from picamera2 import Picamera2
from PIL import Image, ImageTk

# Display size for each panel (camera feed / result)
DISPLAY_W = 580
DISPLAY_H = 380


# ---------------------------------------------------------------------------
# Tag generation
# ---------------------------------------------------------------------------

def generate_tags(tag_ids, size=300, border=80, family_name="DICT_APRILTAG_36h11"):
    """Create printable PNG images of the requested AprilTags."""
    family = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, family_name))
    for tid in tag_ids:
        tag_img = cv2.aruco.generateImageMarker(family, tid, size)
        bordered = cv2.copyMakeBorder(
            tag_img, border, border, border, border,
            cv2.BORDER_CONSTANT, value=255)
        h = bordered.shape[0]
        canvas = cv2.copyMakeBorder(bordered, 0, 40, 0, 0,
                                    cv2.BORDER_CONSTANT, value=255)
        cv2.putText(canvas, f"ID {tid}", (border, h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
        fname = f"apriltag_id{tid}.png"
        cv2.imwrite(fname, canvas)
        print(f"  {fname}  ({canvas.shape[1]}x{canvas.shape[0]} px)")


# ---------------------------------------------------------------------------
# Detection wrapper
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
        resized = cv2.resize(rgb_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = rgb_array
    pil_img = Image.fromarray(resized)
    return ImageTk.PhotoImage(pil_img), new_w, new_h


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class DeskewApp:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.root.title("AprilTag Deskew")
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
        self.last_frame = None
        self.last_detections = []
        self.deskewed_rgb = None
        self.save_count = 0

        self._setup_detector()
        self._setup_camera()
        self._build_gui()
        self._update_feed()

    # -- Initialisation --

    def _setup_detector(self):
        dictionary = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, self.args.family))
        params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(dictionary, params)

    def _setup_camera(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": (self.args.width, self.args.height),
                   "format": "RGB888"})
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(0.5)

    # -- GUI layout --

    def _build_gui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("sans-serif", 10))
        style.configure("Header.TLabel", font=("sans-serif", 11, "bold"),
                         foreground="#89b4fa")
        style.configure("Status.TLabel", font=("sans-serif", 11),
                         foreground="#a6e3a1")
        style.configure("Warn.TLabel", font=("sans-serif", 11),
                         foreground="#fab387")
        style.configure("TButton", font=("sans-serif", 10, "bold"),
                         padding=6)

        # -- Top: two image panels side by side --
        panels = ttk.Frame(self.root)
        panels.pack(padx=8, pady=(8, 4), fill="both", expand=True)

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
        status_frame.pack(padx=8, fill="x")
        self.status_var = tk.StringVar(value="Starting camera...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                      style="Status.TLabel")
        self.status_label.pack(side="left")

        # -- Bottom: controls --
        controls = ttk.Frame(self.root)
        controls.pack(padx=8, pady=(4, 8), fill="x")

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
                         value="single", command=self._mode_changed).pack(side="left", padx=(6, 0))
        ttk.Label(mode_frame, text="  Tag ID:").pack(side="left")
        self.single_id_var = tk.StringVar(
            value=str(self.single_tag_id if self.single_tag_id is not None else 0))
        self.single_id_spin = tk.Spinbox(
            mode_frame, from_=0, to=586, width=4, font=("sans-serif", 10),
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

    # -- Camera feed loop --

    def _update_feed(self):
        if not self.running:
            return

        frame = self.picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        detections = detect_tags(gray, self.detector)

        self.last_frame = frame
        self.last_detections = detections

        # Draw overlay
        vis = draw_overlay(frame, detections)

        # Update status
        found_ids = sorted([d["id"] for d in detections])
        ready = all(t in found_ids for t in self.needed_ids)
        if ready:
            self.status_var.set(
                f"Tags detected: {found_ids}  --  Ready to deskew (Space / click button)")
            self.status_label.configure(style="Status.TLabel")
        else:
            missing = [t for t in self.needed_ids if t not in found_ids]
            self.status_var.set(
                f"Tags detected: {found_ids}  --  Missing: {missing}")
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

        self.root.after(50, self._update_feed)  # ~20 fps

    # -- Actions --

    def do_deskew(self):
        if self.last_frame is None:
            return

        if self.single_tag_id is not None:
            det = next((d for d in self.last_detections
                        if d["id"] == self.single_tag_id), None)
            if det is None:
                self.status_var.set(
                    f"Cannot deskew: tag {self.single_tag_id} not found")
                self.status_label.configure(style="Warn.TLabel")
                return
            result, err = deskew_single_tag(self.last_frame, det)
        else:
            result, err = deskew_four_tags(
                self.last_frame, self.last_detections,
                self.tag_ids, self.output_size)

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
        if self.last_frame is None:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"raw_{ts}.jpg"
        cv2.imwrite(fname, cv2.cvtColor(self.last_frame, cv2.COLOR_RGB2BGR))
        self.status_var.set(f"Saved raw: {fname}")
        self.status_label.configure(style="Status.TLabel")

    def quit(self):
        self.running = False
        self.picam2.stop()
        self.root.destroy()


# ---------------------------------------------------------------------------
# Headless capture (no GUI)
# ---------------------------------------------------------------------------

def headless_capture(args):
    tag_ids = [int(x) for x in args.tags.split(",")]
    output_size = None
    if args.output_size:
        parts = args.output_size.split("x")
        output_size = (int(parts[0]), int(parts[1]))

    dictionary = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, args.family))
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(1)

    frame = picam2.capture_array()
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    detections = detect_tags(gray, detector)
    print(f"Detected tags: {[d['id'] for d in detections]}")

    if args.single_tag is not None:
        det = next((d for d in detections if d["id"] == args.single_tag), None)
        if det is None:
            print(f"Tag {args.single_tag} not found")
            picam2.stop()
            sys.exit(1)
        result, err = deskew_single_tag(frame, det)
    else:
        result, err = deskew_four_tags(frame, detections, tag_ids, output_size)

    if err:
        print(f"Deskew failed: {err}")
        raw_path = str(Path(args.output).with_suffix("")) + "_raw.jpg"
        cv2.imwrite(raw_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        print(f"Saved raw frame: {raw_path}")
        picam2.stop()
        sys.exit(1)

    if output_size:
        result = cv2.resize(result, output_size)
    cv2.imwrite(args.output, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    print(f"Saved deskewed image: {args.output}")
    picam2.stop()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="AprilTag-based image deskewing for RPi camera")

    ap.add_argument("--generate-tags", action="store_true",
                    help="Generate printable tag PNGs and exit")
    ap.add_argument("--capture", action="store_true",
                    help="Headless: capture one frame, deskew, save, exit")
    ap.add_argument("-o", "--output", default="deskewed.jpg",
                    help="Output path for --capture (default: deskewed.jpg)")

    ap.add_argument("--tags", default="0,1,2,3",
                    help="4 tag IDs as TL,TR,BR,BL (default: 0,1,2,3)")
    ap.add_argument("--single-tag", type=int, default=None, metavar="ID",
                    help="Use a single tag for deskewing instead of four")

    ap.add_argument("--family", default="DICT_APRILTAG_36h11",
                    choices=["DICT_APRILTAG_36h11", "DICT_APRILTAG_36h10",
                             "DICT_APRILTAG_25h9", "DICT_APRILTAG_16h5"],
                    help="Tag family (default: DICT_APRILTAG_36h11)")
    ap.add_argument("--width", type=int, default=2304,
                    help="Capture width (default: 2304)")
    ap.add_argument("--height", type=int, default=1296,
                    help="Capture height (default: 1296)")
    ap.add_argument("--output-size", default=None, metavar="WxH",
                    help="Force output size, e.g. 1920x1080")
    args = ap.parse_args()

    tag_ids = [int(x) for x in args.tags.split(",")]
    if len(tag_ids) != 4 and args.single_tag is None:
        ap.error("--tags must specify exactly 4 comma-separated IDs")

    # -- Generate tags mode --
    if args.generate_tags:
        needed = [args.single_tag] if args.single_tag is not None else tag_ids
        print("Generating tag images:")
        generate_tags(needed, family_name=args.family)
        print("\nPrint these and place them on/around your target surface.")
        if args.single_tag is None:
            print("Arrangement (as seen by the camera):")
            print(f"  [{tag_ids[0]}] -------- [{tag_ids[1]}]")
            print(f"   |                |")
            print(f"   |   (your area)  |")
            print(f"   |                |")
            print(f"  [{tag_ids[3]}] -------- [{tag_ids[2]}]")
        return

    # -- Headless capture mode --
    if args.capture:
        headless_capture(args)
        return

    # -- GUI mode --
    root = tk.Tk()
    app = DeskewApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
