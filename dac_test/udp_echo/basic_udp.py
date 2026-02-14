import socket
import time

ESP32_IP = '172.20.10.12'
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Sending 100 packets to {ESP32_IP}:{UDP_PORT}")
print("Check ESP32 serial monitor\n")

for i in range(100):
    data = b'X' * 1000  # 1KB packet
    sock.sendto(data, (ESP32_IP, UDP_PORT))
    print(f"Sent packet {i+1}/100")
    time.sleep(0.05)  # 50ms between packets

sock.close()
print("\nDone! Check ESP32 - how many packets received?")