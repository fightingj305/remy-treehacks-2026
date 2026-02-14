import wave
import socket
import time

ESP32_IP = '172.20.10.12'
WAV_FILE = 'doremi.wav'

wf = wave.open(WAV_FILE, 'rb')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

MAX_PACKET_SIZE = 1024  # Safe size that works
FRAMES_PER_PACKET = MAX_PACKET_SIZE // 4  # 4 bytes per frame (stereo 16-bit)

print(f"Sending with max packet size: {MAX_PACKET_SIZE} bytes")
print(f"Frames per packet: {FRAMES_PER_PACKET}\n")

packet_count = 0
start_time = time.time()

try:
    while True:
        data = wf.readframes(FRAMES_PER_PACKET)
        
        if not data:
            elapsed = time.time() - start_time
            print(f"\nFile complete in {elapsed:.1f}s ({packet_count} packets)")
            wf.rewind()
            time.sleep(1)
            packet_count = 0
            start_time = time.time()
            continue
        
        sock.sendto(data, (ESP32_IP, 12345))
        packet_count += 1
        
        if packet_count % 50 == 0:
            print(f"Sent {packet_count} packets")
        
        # Timing: FRAMES_PER_PACKET frames at 44100 Hz
        time.sleep(FRAMES_PER_PACKET / 44100.0 * 0.8)  # 90% speed to stay ahead

except KeyboardInterrupt:
    print(f"\nStopped at {packet_count} packets")

wf.close()
sock.close()