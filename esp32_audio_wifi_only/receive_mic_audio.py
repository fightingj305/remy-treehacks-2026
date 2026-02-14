import socket
import pyaudio

# --- UDP configuration ---
UDP_IP = "0.0.0.0"  # Listen on all interfaces
UDP_PORT = 12345
BUFFER_SIZE = 1024  # Must match ESP32 packet size

# --- Audio configuration ---
CHANNELS = 1         # Mono
RATE = 44100         # Sample rate
FORMAT = pyaudio.paInt16  # 16-bit PCM

# --- Setup UDP socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"Listening for audio on UDP port {UDP_PORT}...")

# --- Setup PyAudio ---
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=BUFFER_SIZE)

try:
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        # Play received audio
        stream.write(data)
except KeyboardInterrupt:
    print("Stopping...")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
    sock.close()
