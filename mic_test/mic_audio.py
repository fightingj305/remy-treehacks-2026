import socket
import pyaudio

# Audio configuration settings
CHUNK = 1024  # Size of each audio packet (in frames)
FORMAT = pyaudio.paInt16  # Audio data format (16-bit integer)
CHANNELS = 1  # Single channel (mono)
RATE = 16000  # Sampling rate (16 kHz)

# Create a PyAudio object to handle audio streaming
p = pyaudio.PyAudio()

# Open an audio output stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True) # 'output=True' indicates this is a playback stream

# Configure the UDP server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Bind the socket to all available network interfaces on port 8888
server_socket.bind(('0.0.0.0', 8888))
ip_address = server_socket.getsockname()[0]
print(f"Waiting for audio data stream on {ip_address}:8888...")

try:
    # Continuous loop to receive and play audio
    while True:
        # Receive data from the client. The buffer size is CHUNK * 2 because each int16 sample is 2 bytes.
        data, addr = server_socket.recvfrom(CHUNK * 2)

        # If no data is received, break out of the loop
        if not data:
            break

        # Write the received audio data to the output stream for playback
        stream.write(data)

except KeyboardInterrupt:
    # Handle program termination with Ctrl+C
    pass

finally:
    # Clean up resources
    stream.stop_stream()
    stream.close()
    p.terminate()
    server_socket.close()