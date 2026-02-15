"""
receiver_jetson.py — Runs on the Base Station RPi.
Receives camera frames via UDP, forwards to Jetson Nano for processing,
receives processed frames back, and displays both side-by-side.
Also receives VLM analysis text from the Jetson and displays it in a
scrollable log widget.

Usage:
    python3 receiver_jetson.py --port 9000 --jetson-host 192.168.55.1
    python3 receiver_jetson.py --port 9000 --jetson-host 192.168.55.1 \
        --jetson-port 9001 --return-port 9002
"""

import argparse
import socket
import struct
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

# Display size for each panel — sized to fit 800x480 DSI display
DISPLAY_W = 380
DISPLAY_H = 200

MAX_UDP_RECV = 65535

VLM_LOG_LINES = 8


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

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

class ReceiverJetsonApp:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.root.title("Receiver — Jetson Pipeline")
        self.root.geometry("800x480")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.running = True
        self._camera_frame = None
        self._jetson_frame = None
        self._camera_lock = threading.Lock()
        self._jetson_lock = threading.Lock()
        self._camera_connected = False
        self._jetson_connected = False

        # FPS tracking
        self._camera_fps = 0.0
        self._jetson_fps = 0.0
        self._camera_frame_count = 0
        self._jetson_frame_count = 0
        self._camera_fps_time = time.monotonic()
        self._jetson_fps_time = time.monotonic()

        # VLM message state
        self._vlm_messages = []
        self._vlm_lock = threading.Lock()
        self._vlm_max_messages = 50
        self._vlm_rendered_count = 0

        # Socket for forwarding to Jetson (created once, used by camera thread)
        self._fwd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._fwd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
                                  4 * 1024 * 1024)

        self._build_gui()
        self._start_network_threads()
        self._update_display()

    # -- Network threads --

    def _start_network_threads(self):
        threading.Thread(target=self._camera_recv_loop, daemon=True).start()
        threading.Thread(target=self._jetson_recv_loop, daemon=True).start()
        threading.Thread(target=self._vlm_recv_loop, daemon=True).start()

    def _camera_recv_loop(self):
        """Receive camera frames on --port, decode for display, forward to Jetson."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        sock.bind(("0.0.0.0", self.args.port))
        print(f"Listening for camera on UDP port {self.args.port} ...")

        while self.running:
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(MAX_UDP_RECV)
            except socket.timeout:
                continue
            except OSError:
                continue

            if not self._camera_connected:
                print(f"Camera receiving from {addr}")
                self._camera_connected = True

            # Validate
            if len(data) < 4:
                continue
            frame_len = struct.unpack(">I", data[:4])[0]
            jpeg_data = data[4:]
            if len(jpeg_data) != frame_len:
                continue

            # Decode for display
            bgr = cv2.imdecode(
                np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            with self._camera_lock:
                self._camera_frame = rgb

            # Update camera FPS
            self._camera_frame_count += 1
            now = time.monotonic()
            elapsed = now - self._camera_fps_time
            if elapsed >= 1.0:
                self._camera_fps = self._camera_frame_count / elapsed
                self._camera_frame_count = 0
                self._camera_fps_time = now

            # Forward raw datagram to Jetson
            try:
                self._fwd_sock.sendto(
                    data, (self.args.jetson_host, self.args.jetson_port))
            except OSError:
                pass

        sock.close()

    def _jetson_recv_loop(self):
        """Receive processed frames back from Jetson on --return-port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        sock.bind(("0.0.0.0", self.args.return_port))
        print(f"Listening for Jetson return on UDP port {self.args.return_port} ...")

        while self.running:
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(MAX_UDP_RECV)
            except socket.timeout:
                continue
            except OSError:
                continue

            if not self._jetson_connected:
                print(f"Jetson receiving from {addr}")
                self._jetson_connected = True

            # Validate
            if len(data) < 4:
                continue
            frame_len = struct.unpack(">I", data[:4])[0]
            jpeg_data = data[4:]
            if len(jpeg_data) != frame_len:
                continue

            # Decode for display
            bgr = cv2.imdecode(
                np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            with self._jetson_lock:
                self._jetson_frame = rgb

            # Update Jetson FPS
            self._jetson_frame_count += 1
            now = time.monotonic()
            elapsed = now - self._jetson_fps_time
            if elapsed >= 1.0:
                self._jetson_fps = self._jetson_frame_count / elapsed
                self._jetson_frame_count = 0
                self._jetson_fps_time = now

        sock.close()

    def _vlm_recv_loop(self):
        """Receive VLM analysis text from Jetson on --vlm-port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.args.vlm_port))
        print(f"Listening for VLM analysis on UDP port {self.args.vlm_port} ...")

        while self.running:
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(MAX_UDP_RECV)
            except socket.timeout:
                continue
            except OSError:
                continue

            try:
                msg = data.decode("utf-8")
            except UnicodeDecodeError:
                continue

            with self._vlm_lock:
                self._vlm_messages.append(msg)
                if len(self._vlm_messages) > self._vlm_max_messages:
                    self._vlm_messages = self._vlm_messages[-self._vlm_max_messages:]
                    self._vlm_rendered_count = min(
                        self._vlm_rendered_count, len(self._vlm_messages))

        sock.close()

    # -- GUI layout --

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

        # Left panel: original camera feed
        left = ttk.Frame(panels)
        left.pack(side="left", padx=(0, 4), fill="both", expand=True)
        ttk.Label(left, text="Camera Feed (Original)",
                  style="Header.TLabel").pack(anchor="w")
        self.feed_canvas = tk.Canvas(left, width=DISPLAY_W, height=DISPLAY_H,
                                     bg="#181825", highlightthickness=0)
        self.feed_canvas.pack(fill="both", expand=True)
        self._feed_photo = None

        # Right panel: Jetson processed
        right = ttk.Frame(panels)
        right.pack(side="left", padx=(4, 0), fill="both", expand=True)
        ttk.Label(right, text="Jetson Processed",
                  style="Header.TLabel").pack(anchor="w")
        self.result_canvas = tk.Canvas(right, width=DISPLAY_W, height=DISPLAY_H,
                                       bg="#181825", highlightthickness=0)
        self.result_canvas.pack(fill="both", expand=True)
        self._result_photo = None

        # -- VLM Analysis Log --
        vlm_frame = ttk.Frame(self.root)
        vlm_frame.pack(padx=4, pady=(2, 2), fill="x")
        ttk.Label(vlm_frame, text="VLM Analysis Log",
                  style="Header.TLabel").pack(anchor="w")
        self.vlm_text = tk.Text(
            vlm_frame,
            height=VLM_LOG_LINES,
            font=("monospace", 7),
            bg="#181825",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
            wrap="word",
            state="disabled",
        )
        self.vlm_text.pack(fill="x")

        # -- Status bar --
        status_frame = ttk.Frame(self.root)
        status_frame.pack(padx=4, fill="x")
        self.status_var = tk.StringVar(
            value=f"Waiting for camera on port {self.args.port} ...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                      style="Warn.TLabel")
        self.status_label.pack(side="left")

        # -- Controls --
        controls = ttk.Frame(self.root)
        controls.pack(padx=4, pady=(2, 4), fill="x")

        ttk.Button(controls, text="Save Raw",
                   command=self.save_raw).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Save Processed",
                   command=self.save_processed).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Quit",
                   command=self.quit).pack(side="left", padx=(0, 6))

        # Keyboard shortcuts
        self.root.bind("r", lambda e: self.save_raw())
        self.root.bind("p", lambda e: self.save_processed())
        self.root.bind("q", lambda e: self.quit())
        self.root.bind("<Escape>", lambda e: self.quit())

    # -- Display update loop --

    def _update_display(self):
        if not self.running:
            return

        with self._camera_lock:
            camera_frame = self._camera_frame
        with self._jetson_lock:
            jetson_frame = self._jetson_frame

        # Render left panel (camera)
        if camera_frame is not None:
            cw = self.feed_canvas.winfo_width()
            ch = self.feed_canvas.winfo_height()
            if cw < 2 or ch < 2:
                cw, ch = DISPLAY_W, DISPLAY_H
            photo, _, _ = rgb_to_photoimage(camera_frame, cw, ch)
            self._feed_photo = photo
            self.feed_canvas.delete("all")
            self.feed_canvas.create_image(cw // 2, ch // 2, image=photo)

        # Render right panel (Jetson processed)
        if jetson_frame is not None:
            cw = self.result_canvas.winfo_width()
            ch = self.result_canvas.winfo_height()
            if cw < 2 or ch < 2:
                cw, ch = DISPLAY_W, DISPLAY_H
            photo, _, _ = rgb_to_photoimage(jetson_frame, cw, ch)
            self._result_photo = photo
            self.result_canvas.delete("all")
            self.result_canvas.create_image(cw // 2, ch // 2, image=photo)

        # Append new VLM messages to text widget
        with self._vlm_lock:
            new_msgs = self._vlm_messages[self._vlm_rendered_count:]
            self._vlm_rendered_count = len(self._vlm_messages)
        if new_msgs:
            self.vlm_text.configure(state="normal")
            for msg in new_msgs:
                self.vlm_text.insert("end", msg + "\n")
            self.vlm_text.see("end")
            self.vlm_text.configure(state="disabled")

        # Update status bar
        if not self._camera_connected:
            self.status_var.set(
                f"Waiting for camera on port {self.args.port} ...")
            self.status_label.configure(style="Warn.TLabel")
        elif camera_frame is not None:
            fh, fw = camera_frame.shape[:2]
            cam_str = f"Cam: {fw}x{fh} {self._camera_fps:.0f}fps"
            if self._jetson_connected and jetson_frame is not None:
                jh, jw = jetson_frame.shape[:2]
                jet_str = f"Jetson: {jw}x{jh} {self._jetson_fps:.0f}fps"
                self.status_var.set(f"{cam_str} | {jet_str}")
                self.status_label.configure(style="Status.TLabel")
            else:
                self.status_var.set(
                    f"{cam_str} | Jetson: waiting on port "
                    f"{self.args.return_port} ...")
                self.status_label.configure(style="Warn.TLabel")

        self.root.after(50, self._update_display)

    # -- Actions --

    def save_raw(self):
        with self._camera_lock:
            frame = self._camera_frame
        if frame is None:
            self.status_var.set("No camera frame to save")
            self.status_label.configure(style="Warn.TLabel")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"raw_{ts}.jpg"
        cv2.imwrite(fname, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        self.status_var.set(f"Saved raw: {fname}")
        self.status_label.configure(style="Status.TLabel")

    def save_processed(self):
        with self._jetson_lock:
            frame = self._jetson_frame
        if frame is None:
            self.status_var.set("No processed frame to save")
            self.status_label.configure(style="Warn.TLabel")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"processed_{ts}.jpg"
        cv2.imwrite(fname, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        self.status_var.set(f"Saved processed: {fname}")
        self.status_label.configure(style="Status.TLabel")

    def quit(self):
        self.running = False
        self.root.destroy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Base Station: camera receiver with Jetson forwarding")
    ap.add_argument("--port", type=int, default=9000,
                    help="UDP port to receive camera frames (default 9000)")
    ap.add_argument("--jetson-host", default="192.168.55.1",
                    help="Jetson Nano IP (default 192.168.55.1)")
    ap.add_argument("--jetson-port", type=int, default=9001,
                    help="UDP port to send frames to Jetson (default 9001)")
    ap.add_argument("--return-port", type=int, default=9002,
                    help="UDP port to receive processed frames from Jetson "
                         "(default 9002)")
    ap.add_argument("--vlm-port", type=int, default=9003,
                    help="UDP port to receive VLM analysis text (default 9003)")
    args = ap.parse_args()

    root = tk.Tk()
    ReceiverJetsonApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
