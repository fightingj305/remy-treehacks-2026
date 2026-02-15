"""
receiver_jetson_full.py — Unified Base Station: video pipeline + voice AI.

Receives camera frames via UDP, forwards to Jetson for processing,
receives processed frames back, displays both side-by-side with VLM log.

Additionally receives ESP32 microphone audio, runs Silero VAD to detect
speech, transcribes via ElevenLabs STT, queries Claude (with VLM scene
context) for a concise answer, generates TTS via ElevenLabs, and streams
the audio back to the ESP32 speaker.

Usage:
    python3 receiver_jetson_full.py --port 9000 --jetson-host 192.168.55.1
    python3 receiver_jetson_full.py --port 9000 --jetson-host 192.168.55.1 \
        --esp32-host 172.20.10.12
"""

import argparse
import glob as globmod
import io
import json
import os
import socket
import struct
import subprocess
import threading
import time
import tkinter as tk
import wave
from datetime import datetime
from tkinter import ttk

import anthropic
import cv2
import numpy as np
import torch
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from PIL import Image, ImageTk
from scipy.signal import resample_poly
from silero_vad import load_silero_vad, VADIterator

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Display size for each panel — sized to fit 800x480 DSI display
DISPLAY_W = 380
DISPLAY_H = 200
MAX_UDP_RECV = 65535
VLM_LOG_LINES = 8

# Audio constants
AUDIO_RATE = 44100        # Sample rate from ESP32
VAD_RATE = 16000          # Silero VAD expected rate
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2    # 16-bit
AUDIO_BUFFER_SIZE = 1024  # UDP packet size from ESP32

# VAD configuration
VAD_CHUNK_SAMPLES = 512   # Silero requires exactly 512 samples at 16kHz
MIN_SILENCE_DURATION_MS = 700
SPEECH_PAD_MS = 300
VAD_THRESHOLD = 0.3

# ElevenLabs TTS config
TTS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
TTS_MODEL_ID = "eleven_multilingual_v2"
TTS_OUTPUT_FORMAT = "mp3_44100_128"

# Claude config
CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_SYSTEM_PROMPT = (
    "You are a conversational AI kitchen helper. You are given a log of "
    "visual scene analysis from a kitchen camera and a question from the "
    "user. Give concise answers (1-3 sentences) as your output will be "
    "fed into text-to-speech."
)

# TTS streaming to ESP32
TTS_MAX_PACKET_SIZE = 1024
TTS_FRAMES_PER_PACKET = TTS_MAX_PACKET_SIZE // (AUDIO_SAMPLE_WIDTH * 2)  # stereo

# Recipe TCP server
RECIPE_PORT = 9005

# ---------------------------------------------------------------------------
# DS18B20 temperature sensor helpers
# ---------------------------------------------------------------------------

W1_DEVICES_PATH = "/sys/bus/w1/devices/"
DS18B20_PREFIX = "28-"


def find_sensor():
    """Find the first DS18B20 device directory."""
    devices = globmod.glob(os.path.join(W1_DEVICES_PATH, DS18B20_PREFIX + "*"))
    if not devices:
        return None
    return devices[0]


def read_temperature(device_path):
    """Read temperature in Celsius from the sensor's sysfs file."""
    slave_file = os.path.join(device_path, "w1_slave")
    try:
        with open(slave_file, "r") as f:
            lines = f.readlines()
    except OSError:
        return None

    if len(lines) < 2 or "YES" not in lines[0]:
        return None

    idx = lines[1].find("t=")
    if idx == -1:
        return None

    raw = int(lines[1][idx + 2:])
    return raw / 1000.0


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


def resample_audio(audio_44k, up=160, down=441):
    """Resample audio from 44100 Hz to 16000 Hz using scipy.

    Args:
        audio_44k: numpy int16 array at 44100 Hz
        up: upsample factor (160 for 44100→16000)
        down: downsample factor (441 for 44100→16000)

    Returns:
        torch float32 tensor at 16000 Hz, normalized to [-1, 1]
    """
    audio_float = audio_44k.astype(np.float32) / 32768.0
    resampled = resample_poly(audio_float, up, down)
    return torch.from_numpy(resampled.astype(np.float32))


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class ReceiverJetsonFullApp:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.root.title("Receiver — Jetson Pipeline + Voice AI")
        self.root.geometry("800x480")
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.running = True

        # Video state
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

        # DS18B20 temperature state
        self._temp_c = None
        self._temp_lock = threading.Lock()
        self._sensor_path = find_sensor()
        if self._sensor_path:
            print(f"DS18B20 sensor found: {os.path.basename(self._sensor_path)}")
        else:
            print("DS18B20 sensor not found — temperature display disabled")

        # Voice AI state
        self._voice_state = "Listening"
        self._voice_lock = threading.Lock()
        self._last_speak_end = 0.0  # monotonic timestamp of last TTS finish
        self._speak_cooldown = 7.0  # seconds to ignore VAD after speaking

        # Manual recording state (for Ask button)
        self._manual_recording = False
        self._manual_chunks = []
        self._manual_lock = threading.Lock()

        # Lock to serialize TTS output — prevents interleaved audio packets
        self._tts_lock = threading.Lock()

        # Shared socket for TTS output to ESP32 (reused across all queries)
        self._tts_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._tts_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
                                  4 * 1024 * 1024)

        # Recipe steps state
        self._recipe_steps = []
        self._recipe_lock = threading.Lock()
        self._recipe_rendered_count = 0

        # Socket for forwarding to Jetson
        self._fwd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._fwd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
                                  4 * 1024 * 1024)

        # API clients
        self._claude_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        self._elevenlabs_client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        )

        # Load Silero VAD (ONNX mode — avoids torch.jit issues on RPi)
        print("Loading Silero VAD (ONNX)...")
        self._vad_model = load_silero_vad(onnx=True)
        print("Silero VAD loaded.")
        self._vad_iterator = VADIterator(
            self._vad_model,
            threshold=VAD_THRESHOLD,
            sampling_rate=VAD_RATE,
            min_silence_duration_ms=MIN_SILENCE_DURATION_MS,
            speech_pad_ms=SPEECH_PAD_MS,
        )

        self._build_gui()
        self._start_network_threads()
        self._update_display()

    # -- Network threads --

    def _start_network_threads(self):
        threading.Thread(target=self._camera_recv_loop, daemon=True).start()
        threading.Thread(target=self._jetson_recv_loop, daemon=True).start()
        threading.Thread(target=self._vlm_recv_loop, daemon=True).start()
        threading.Thread(target=self._audio_recv_loop, daemon=True).start()
        threading.Thread(target=self._recipe_tcp_loop, daemon=True).start()
        if self._sensor_path:
            threading.Thread(target=self._temp_poll_loop, daemon=True).start()

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

            if len(data) < 4:
                continue
            frame_len = struct.unpack(">I", data[:4])[0]
            jpeg_data = data[4:]
            if len(jpeg_data) != frame_len:
                continue

            bgr = cv2.imdecode(
                np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            with self._camera_lock:
                self._camera_frame = rgb

            self._camera_frame_count += 1
            now = time.monotonic()
            elapsed = now - self._camera_fps_time
            if elapsed >= 1.0:
                self._camera_fps = self._camera_frame_count / elapsed
                self._camera_frame_count = 0
                self._camera_fps_time = now

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

            if len(data) < 4:
                continue
            frame_len = struct.unpack(">I", data[:4])[0]
            jpeg_data = data[4:]
            if len(jpeg_data) != frame_len:
                continue

            bgr = cv2.imdecode(
                np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            with self._jetson_lock:
                self._jetson_frame = rgb

            self._jetson_frame_count += 1
            now = time.monotonic()
            elapsed = now - self._jetson_fps_time
            if elapsed >= 1.0:
                self._jetson_fps = self._jetson_frame_count / elapsed
                self._jetson_frame_count = 0
                self._jetson_fps_time = now

        sock.close()

    def _temp_poll_loop(self):
        """Poll the DS18B20 sensor every second."""
        while self.running:
            temp = read_temperature(self._sensor_path)
            with self._temp_lock:
                self._temp_c = temp
            time.sleep(1)

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

            with self._temp_lock:
                temp = self._temp_c
            if temp is not None:
                msg = f"{msg}  [Temp: {temp:.1f}\u00b0C / {temp * 9 / 5 + 32:.1f}\u00b0F]"

            with self._vlm_lock:
                self._vlm_messages.append(msg)
                if len(self._vlm_messages) > self._vlm_max_messages:
                    self._vlm_messages = self._vlm_messages[
                        -self._vlm_max_messages:]
                    self._vlm_rendered_count = min(
                        self._vlm_rendered_count, len(self._vlm_messages))

        sock.close()

    def _recipe_tcp_loop(self):
        """TCP server for receiving recipe steps (length-prefixed JSON)."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("0.0.0.0", self.args.recipe_port))
        server_sock.listen(5)
        print(f"Recipe TCP server listening on port {self.args.recipe_port} ...")

        while self.running:
            server_sock.settimeout(1.0)
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            # Handle client in a separate thread to avoid blocking
            threading.Thread(
                target=self._handle_recipe_client,
                args=(client_sock, addr),
                daemon=True,
            ).start()

        server_sock.close()

    def _handle_recipe_client(self, client_sock, addr):
        """Handle a single recipe TCP client connection."""
        try:
            # Read 4-byte length header
            header = client_sock.recv(4)
            if len(header) != 4:
                print(f"Recipe connection from {addr}: incomplete header")
                client_sock.close()
                return

            payload_len = struct.unpack('>I', header)[0]
            if payload_len > 10 * 1024 * 1024:  # 10 MB max
                print(f"Recipe connection from {addr}: payload too large ({payload_len} bytes)")
                client_sock.close()
                return

            # Read payload
            payload = b''
            while len(payload) < payload_len:
                chunk = client_sock.recv(min(4096, payload_len - len(payload)))
                if not chunk:
                    break
                payload += chunk

            if len(payload) != payload_len:
                print(f"Recipe connection from {addr}: incomplete payload "
                      f"(got {len(payload)}, expected {payload_len})")
                client_sock.close()
                return

            # Parse JSON array
            try:
                recipe_steps = json.loads(payload.decode('utf-8'))
                if not isinstance(recipe_steps, list):
                    print(f"Recipe connection from {addr}: payload is not an array")
                    client_sock.close()
                    return

                # Update recipe steps
                with self._recipe_lock:
                    self._recipe_steps = recipe_steps
                    self._recipe_rendered_count = 0

                print(f"Received recipe from {addr} with {len(recipe_steps)} steps")
                self._append_vlm_message(f"[RECIPE] Received recipe with {len(recipe_steps)} steps")

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Recipe connection from {addr}: JSON decode error: {e}")

        except Exception as e:
            print(f"Recipe connection from {addr}: error: {e}")
        finally:
            client_sock.close()

    # -- Audio / Voice AI threads --

    def _audio_recv_loop(self):
        """Receive ESP32 mic audio, run VAD, trigger voice query on speech end."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.args.audio_port))
        print(f"Listening for ESP32 audio on UDP port {self.args.audio_port} ...")

        # Calculate how many 44.1 kHz bytes we need per VAD chunk
        samples_needed_44k = int(VAD_CHUNK_SAMPLES * AUDIO_RATE / VAD_RATE)
        bytes_needed = samples_needed_44k * AUDIO_SAMPLE_WIDTH

        packet_buffer = b''
        is_recording = False
        recorded_chunks = []
        chunk_count = 0

        while self.running:
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(AUDIO_BUFFER_SIZE)
            except socket.timeout:
                continue
            except OSError:
                continue

            # Collect chunks for manual recording (Ask button)
            with self._manual_lock:
                if self._manual_recording:
                    self._manual_chunks.append(data)

            # Check cooldown — skip VAD while in post-speech cooldown
            if time.monotonic() - self._last_speak_end < self._speak_cooldown:
                continue

            packet_buffer += data

            while len(packet_buffer) >= bytes_needed:
                chunk_original = packet_buffer[:bytes_needed]
                packet_buffer = packet_buffer[bytes_needed:]

                # Convert to numpy int16
                audio_44k = np.frombuffer(chunk_original, dtype=np.int16).copy()

                # Resample 44100 → 16000 using scipy
                audio_16k = resample_audio(audio_44k)

                # Ensure exactly 512 samples
                if len(audio_16k) < VAD_CHUNK_SAMPLES:
                    padding = VAD_CHUNK_SAMPLES - len(audio_16k)
                    audio_16k = torch.nn.functional.pad(audio_16k, (0, padding))
                elif len(audio_16k) > VAD_CHUNK_SAMPLES:
                    audio_16k = audio_16k[:VAD_CHUNK_SAMPLES]

                chunk_count += 1

                # Get speech probability
                with torch.no_grad():
                    speech_prob = self._vad_model(audio_16k, VAD_RATE).item()

                if chunk_count % 30 == 0:
                    print(f"Audio chunk {chunk_count}: "
                          f"speech_prob={speech_prob:.3f}")

                # Process with VAD iterator
                speech_dict = self._vad_iterator(
                    audio_16k, return_seconds=False)

                if is_recording:
                    recorded_chunks.append(chunk_original)

                if speech_dict:
                    if 'start' in speech_dict and not is_recording:
                        print("Speech detected!")
                        is_recording = True
                        recorded_chunks = [chunk_original]
                        with self._voice_lock:
                            self._voice_state = "Recording..."

                    if 'end' in speech_dict and is_recording:
                        print("Speech ended, processing...")
                        is_recording = False
                        # Spawn processing in a separate thread
                        chunks_copy = list(recorded_chunks)
                        recorded_chunks = []
                        threading.Thread(
                            target=self._process_voice_query,
                            args=(chunks_copy,),
                            daemon=True,
                        ).start()

        sock.close()

    def _process_voice_query(self, audio_chunks):
        """Full voice AI pipeline: STT → Claude → TTS → ESP32."""
        with self._voice_lock:
            self._voice_state = "Transcribing..."

        # --- Step 1: Transcribe audio with ElevenLabs STT ---
        transcription = self._transcribe_audio(audio_chunks)
        if not transcription:
            print("No transcription result, returning to listening.")
            with self._voice_lock:
                self._voice_state = "Listening"
            return

        print(f"Transcription: {transcription}")
        self._append_vlm_message(f"[USER] {transcription}")

        # --- Step 2: Build context from VLM messages and recipe steps ---
        with self._voice_lock:
            self._voice_state = "Thinking..."

        with self._vlm_lock:
            vlm_context = "\n".join(self._vlm_messages[-20:])

        with self._recipe_lock:
            recipe_steps = list(self._recipe_steps)

        # --- Step 3: Query Claude ---
        response_text = self._query_claude(transcription, vlm_context, recipe_steps)
        if not response_text:
            print("No Claude response, returning to listening.")
            with self._voice_lock:
                self._voice_state = "Listening"
            return

        print(f"Claude response: {response_text}")
        self._append_vlm_message(f"[ASSISTANT] {response_text}")

        # --- Step 4: Generate TTS and stream to ESP32 ---
        with self._voice_lock:
            self._voice_state = "Speaking..."

        self._speak_to_esp32(response_text)

        # Start cooldown so VAD doesn't trigger on the TTS playback
        self._last_speak_end = time.monotonic()

        with self._voice_lock:
            self._voice_state = "Cooldown"

    def _transcribe_audio(self, audio_chunks):
        """Transcribe recorded audio chunks via ElevenLabs STT."""
        if not audio_chunks:
            return None

        audio_data = b''.join(audio_chunks)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(AUDIO_SAMPLE_WIDTH)
            wf.setframerate(AUDIO_RATE)
            wf.writeframes(audio_data)
        wav_buffer.seek(0)

        try:
            transcription = self._elevenlabs_client.speech_to_text.convert(
                file=wav_buffer,
                model_id="scribe_v2",
                tag_audio_events=False,
                language_code="eng",
                diarize=False,
            )
            text = transcription.text.strip()
            return text if text else None
        except Exception as e:
            print(f"STT error: {e}")
            return None

    def _query_claude(self, question, vlm_context, recipe_steps):
        """Query Claude with the user's question, VLM scene context, and recipe steps."""
        context_parts = []

        if recipe_steps:
            recipe_text = "\n".join(
                f"{i}. {step}" for i, step in enumerate(recipe_steps, 1)
            )
            context_parts.append(
                f"The user is following this recipe:\n\n{recipe_text}\n"
            )

        if vlm_context:
            context_parts.append(
                f"Here is the recent visual scene analysis log from the "
                f"kitchen camera:\n\n{vlm_context}\n"
            )

        if context_parts:
            user_message = "\n".join(context_parts) + f"\nUser question: {question}"
        else:
            user_message = f"User question: {question}"

        try:
            response = self._claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=256,
                system=CLAUDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def _speak_to_esp32(self, text):
        """Generate TTS audio and stream to ESP32 via UDP.

        Serialized with _tts_lock so concurrent voice queries never
        interleave audio packets on the wire.
        """
        with self._tts_lock:
            try:
                # Generate speech with ElevenLabs
                audio_gen = self._elevenlabs_client.text_to_speech.convert(
                    text=text,
                    voice_id=TTS_VOICE_ID,
                    model_id=TTS_MODEL_ID,
                    output_format=TTS_OUTPUT_FORMAT,
                )
                audio_bytes = b''.join(audio_gen)

                # Convert MP3 to WAV via ffmpeg
                process = subprocess.Popen(
                    [
                        'ffmpeg', '-i', 'pipe:0',
                        '-f', 'wav', '-acodec', 'pcm_s16le',
                        '-ar', str(AUDIO_RATE),
                        '-ac', '2',  # Stereo for ESP32 DAC
                        'pipe:1',
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                wav_data, _ = process.communicate(input=audio_bytes)

                # Stream WAV PCM data to ESP32 using the shared socket
                wf = wave.open(io.BytesIO(wav_data), 'rb')

                esp32_addr = (self.args.esp32_host, self.args.esp32_audio_port)
                print(f"Streaming TTS to ESP32 at {esp32_addr} "
                      f"({wf.getnframes() / wf.getframerate():.1f}s)")

                while True:
                    data = wf.readframes(TTS_FRAMES_PER_PACKET)
                    if not data:
                        break
                    self._tts_sock.sendto(data, esp32_addr)
                    time.sleep(TTS_FRAMES_PER_PACKET / AUDIO_RATE * 0.8)

                wf.close()
                print("TTS streaming complete.")

            except Exception as e:
                print(f"TTS/streaming error: {e}")

    def _append_vlm_message(self, msg):
        """Thread-safe append to VLM messages (shown in GUI log)."""
        with self._vlm_lock:
            self._vlm_messages.append(msg)
            if len(self._vlm_messages) > self._vlm_max_messages:
                self._vlm_messages = self._vlm_messages[
                    -self._vlm_max_messages:]
                self._vlm_rendered_count = min(
                    self._vlm_rendered_count, len(self._vlm_messages))

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

        left = ttk.Frame(panels)
        left.pack(side="left", padx=(0, 4), fill="both", expand=True)
        ttk.Label(left, text="Camera Feed (Original)",
                  style="Header.TLabel").pack(anchor="w")
        self.feed_canvas = tk.Canvas(left, width=DISPLAY_W, height=DISPLAY_H,
                                     bg="#181825", highlightthickness=0)
        self.feed_canvas.pack(fill="both", expand=True)
        self._feed_photo = None

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

        # -- Recipe Steps Display --
        recipe_frame = ttk.Frame(self.root)
        recipe_frame.pack(padx=4, pady=(2, 2), fill="x")
        ttk.Label(recipe_frame, text="Recipe Steps",
                  style="Header.TLabel").pack(anchor="w")
        self.recipe_text = tk.Text(
            recipe_frame,
            height=4,
            font=("monospace", 8),
            bg="#181825",
            fg="#a6e3a1",
            insertbackground="#a6e3a1",
            relief="flat",
            wrap="word",
            state="disabled",
        )
        self.recipe_text.pack(fill="x")

        # -- Status bar --
        status_frame = ttk.Frame(self.root)
        status_frame.pack(padx=4, fill="x")
        self.status_var = tk.StringVar(
            value=f"Waiting for camera on port {self.args.port} ...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                      style="Warn.TLabel")
        self.status_label.pack(side="left")

        # Voice AI state indicator
        self.voice_var = tk.StringVar(value="Voice: Listening")
        style.configure("Voice.TLabel", font=("sans-serif", 9, "bold"),
                         foreground="#b4befe", background="#1e1e2e")
        self.voice_label = ttk.Label(status_frame, textvariable=self.voice_var,
                                     style="Voice.TLabel")
        self.voice_label.pack(side="right", padx=(8, 0))

        # Temperature display
        self.temp_var = tk.StringVar(value="Temp: --")
        style.configure("Temp.TLabel", font=("sans-serif", 9, "bold"),
                         foreground="#f38ba8", background="#1e1e2e")
        self.temp_label = ttk.Label(status_frame, textvariable=self.temp_var,
                                    style="Temp.TLabel")
        self.temp_label.pack(side="right")

        # -- Controls --
        controls = ttk.Frame(self.root)
        controls.pack(padx=4, pady=(2, 4), fill="x")

        self.ask_btn = ttk.Button(controls, text="Ask",
                                   command=self._toggle_ask)
        self.ask_btn.pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Save Raw",
                   command=self.save_raw).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Save Processed",
                   command=self.save_processed).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Quit",
                   command=self.quit).pack(side="left", padx=(0, 6))

        # Keyboard shortcuts
        self.root.bind("a", lambda e: self._toggle_ask())
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

        # Render recipe steps
        with self._recipe_lock:
            recipe_steps = list(self._recipe_steps)
            recipe_rendered_count = self._recipe_rendered_count
        if recipe_rendered_count == 0 and recipe_steps:
            self.recipe_text.configure(state="normal")
            self.recipe_text.delete("1.0", "end")
            for i, step in enumerate(recipe_steps, 1):
                self.recipe_text.insert("end", f"{i}. {step}\n")
            self.recipe_text.configure(state="disabled")
            with self._recipe_lock:
                self._recipe_rendered_count = 1

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

        # Update temperature display
        with self._temp_lock:
            temp = self._temp_c
        if temp is not None:
            self.temp_var.set(
                f"Temp: {temp:.1f}\u00b0C / {temp * 9 / 5 + 32:.1f}\u00b0F")
        elif self._sensor_path is None:
            self.temp_var.set("Temp: no sensor")

        # Update voice state (show cooldown remaining if active)
        cooldown_remaining = self._speak_cooldown - (
            time.monotonic() - self._last_speak_end)
        with self._voice_lock:
            voice_state = self._voice_state
            if voice_state == "Cooldown" and cooldown_remaining <= 0:
                self._voice_state = "Listening"
                voice_state = "Listening"
        if voice_state == "Cooldown" and cooldown_remaining > 0:
            self.voice_var.set(f"Voice: Cooldown ({cooldown_remaining:.0f}s)")
        else:
            self.voice_var.set(f"Voice: {voice_state}")

        self.root.after(50, self._update_display)

    # -- Actions --

    def _toggle_ask(self):
        """Toggle manual recording. Press to start, press again to stop & send."""
        with self._manual_lock:
            if self._manual_recording:
                # Stop recording and process
                self._manual_recording = False
                chunks = self._manual_chunks
                self._manual_chunks = []
            else:
                # Start recording
                self._manual_recording = True
                self._manual_chunks = []
                with self._voice_lock:
                    self._voice_state = "Recording (manual)..."
                self.ask_btn.configure(text="Stop")
                print("Manual recording started (press Ask/a again to stop)")
                return

        # Process the recorded audio
        self.ask_btn.configure(text="Ask")
        if not chunks:
            print("No audio captured.")
            with self._voice_lock:
                self._voice_state = "Listening"
            return

        # Combine raw UDP packets into VAD-sized chunks for STT
        raw_audio = b''.join(chunks)
        # Split into chunks matching the expected format for _process_voice_query
        samples_needed_44k = int(VAD_CHUNK_SAMPLES * AUDIO_RATE / VAD_RATE)
        bytes_needed = samples_needed_44k * AUDIO_SAMPLE_WIDTH
        audio_chunks = []
        for i in range(0, len(raw_audio) - bytes_needed + 1, bytes_needed):
            audio_chunks.append(raw_audio[i:i + bytes_needed])
        # Include any remaining bytes as a final chunk
        remainder = len(raw_audio) % bytes_needed
        if remainder > 0:
            audio_chunks.append(raw_audio[-(remainder):])

        print(f"Manual recording stopped: {len(raw_audio)} bytes, "
              f"{len(raw_audio) / (AUDIO_RATE * AUDIO_SAMPLE_WIDTH):.1f}s")
        threading.Thread(
            target=self._process_voice_query,
            args=(audio_chunks,),
            daemon=True,
        ).start()

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
        description="Base Station: camera receiver + Jetson forwarding + "
                    "Voice AI pipeline")
    # Video args (same as receiver_jetson.py)
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

    # Audio / Voice AI args
    ap.add_argument("--audio-port", type=int, default=12345,
                    help="UDP port to receive ESP32 mic audio (default 12345)")
    ap.add_argument("--esp32-host", default="172.20.10.12",
                    help="ESP32 IP for TTS playback (default 172.20.10.12)")
    ap.add_argument("--esp32-audio-port", type=int, default=12345,
                    help="UDP port to send TTS audio to ESP32 (default 12345)")

    # Recipe TCP server args
    ap.add_argument("--recipe-port", type=int, default=9005,
                    help="TCP port to receive recipe steps (default 9005)")

    args = ap.parse_args()

    root = tk.Tk()
    ReceiverJetsonFullApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
