from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os
import socket
import time
import io
import wave
import subprocess

load_dotenv()

ESP32_IP = '172.20.10.12'
MAX_PACKET_SIZE = 1024
FRAMES_PER_PACKET = MAX_PACKET_SIZE // 4  # 4 bytes per frame (stereo 16-bit)

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# Get audio from ElevenLabs
audio = elevenlabs.text_to_speech.convert(
    text="It's fucking raw!",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

# Convert generator to bytes
audio_bytes = b''.join(audio)

# Convert MP3 to WAV using ffmpeg
process = subprocess.Popen([
    'ffmpeg',
    '-i', 'pipe:0',
    '-f', 'wav',
    '-acodec', 'pcm_s16le',
    '-ar', '44100',
    '-ac', '2',  # Stereo
    'pipe:1'
], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

wav_data, _ = process.communicate(input=audio_bytes)

# Open WAV data
wf = wave.open(io.BytesIO(wav_data), 'rb')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Sending with max packet size: {MAX_PACKET_SIZE} bytes")
print(f"Frames per packet: {FRAMES_PER_PACKET}")
print(f"Audio duration: {wf.getnframes() / wf.getframerate():.2f}s\n")

packet_count = 0
start_time = time.time()

try:
    while True:
        data = wf.readframes(FRAMES_PER_PACKET)
        
        if not data:
            elapsed = time.time() - start_time
            print(f"\nPlayback complete in {elapsed:.1f}s ({packet_count} packets)")
            break
        
        sock.sendto(data, (ESP32_IP, 12345))
        packet_count += 1
        
        if packet_count % 50 == 0:
            print(f"Sent {packet_count} packets")
        
        # Timing: FRAMES_PER_PACKET frames at 44100 Hz
        time.sleep(FRAMES_PER_PACKET / 44100.0 * 0.8)

except KeyboardInterrupt:
    print(f"\nStopped at {packet_count} packets")

wf.close()
sock.close()