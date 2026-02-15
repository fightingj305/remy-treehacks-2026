import socket
import pyaudio
import os
from dotenv import load_dotenv
from io import BytesIO
import wave
from elevenlabs.client import ElevenLabs
import torch
import numpy as np
import torchaudio

load_dotenv()

# --- Load Silero VAD model ---
print("Loading Silero VAD model...")
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

print("Model loaded successfully!")

# --- UDP configuration ---
UDP_IP = "0.0.0.0"
UDP_PORT = 12345
BUFFER_SIZE = 1024

# --- Audio configuration ---
CHANNELS = 1
RATE_RECEIVE = 44100  # Rate we receive from ESP32
RATE_VAD = 16000      # Rate for VAD processing
FORMAT = pyaudio.paInt16

# --- VAD configuration ---
VAD_CHUNK_SAMPLES = 512  # Silero requires exactly 512 samples at 16kHz
MIN_SILENCE_DURATION_MS = 700
SPEECH_PAD_MS = 300

vad_iterator = VADIterator(
    model,
    threshold=0.3,
    sampling_rate=RATE_VAD,
    min_silence_duration_ms=MIN_SILENCE_DURATION_MS,
    speech_pad_ms=SPEECH_PAD_MS
)

# --- Create resampler ---
resampler = torchaudio.transforms.Resample(
    orig_freq=RATE_RECEIVE,
    new_freq=RATE_VAD
)

# --- Create ElevenLabs client ---
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# --- Setup UDP socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"Listening for audio on UDP port {UDP_PORT}...")
print(f"VAD Threshold: 0.3 (lower = more sensitive)")

# Calculate buffer requirements - need exact samples
samples_needed_44k = int(VAD_CHUNK_SAMPLES * RATE_RECEIVE / RATE_VAD)
bytes_needed = samples_needed_44k * 2
print(f"Need {bytes_needed} bytes per VAD chunk ({samples_needed_44k} samples at 44.1kHz)")
print("Waiting for speech...\n")

# --- Setup PyAudio for playback at original rate ---
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE_RECEIVE,
                output=True,
                frames_per_buffer=BUFFER_SIZE)

# --- State variables ---
packet_buffer_vad = b''
is_recording = False
recorded_chunks_original = []
chunk_count = 0
packet_count = 0

def transcribe_audio():
    global recorded_chunks_original
    
    if len(recorded_chunks_original) == 0:
        print("⚠️ No audio to transcribe")
        return
    
    print(f"📊 Transcribing {len(recorded_chunks_original)} chunks...")
    
    # Concatenate all recorded audio at original rate
    audio_data = b''.join(recorded_chunks_original)
    
    # Create WAV file in memory at original rate for better quality
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE_RECEIVE)
        wf.writeframes(audio_data)
    
    wav_buffer.seek(0)
    
    # Transcribe with ElevenLabs
    try:
        transcription = elevenlabs.speech_to_text.convert(
            file=wav_buffer,
            model_id="scribe_v2",
            tag_audio_events=False,
            language_code="eng",
            diarize=False,
        )
        
        print(f"\n📝 Transcription: {transcription.text}\n")
        print("Waiting for speech...")
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
    
    recorded_chunks_original = []

try:
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        packet_count += 1
        
        # Play received audio at original rate
        stream.write(data)
        
        # Add to VAD buffer
        packet_buffer_vad += data
        
        while len(packet_buffer_vad) >= bytes_needed:
            chunk_original = packet_buffer_vad[:bytes_needed]
            packet_buffer_vad = packet_buffer_vad[bytes_needed:]
            
            # Convert to numpy array
            audio_44k = np.frombuffer(chunk_original, dtype=np.int16)
            
            # Convert to float tensor
            audio_44k_float = torch.from_numpy(audio_44k.copy()).float() / 32768.0
            
            # Resample using torchaudio (more accurate)
            audio_16k_float = resampler(audio_44k_float)
            
            # Ensure exactly 512 samples by padding or trimming
            if len(audio_16k_float) < VAD_CHUNK_SAMPLES:
                # Pad with zeros
                padding = VAD_CHUNK_SAMPLES - len(audio_16k_float)
                audio_16k_float = torch.nn.functional.pad(audio_16k_float, (0, padding))
            elif len(audio_16k_float) > VAD_CHUNK_SAMPLES:
                # Trim
                audio_16k_float = audio_16k_float[:VAD_CHUNK_SAMPLES]
            
            chunk_count += 1
            
            # Get raw speech probability for debugging
            with torch.no_grad():
                speech_prob = model(audio_16k_float, RATE_VAD).item()
            
            # Print probability every 30 chunks
            # if chunk_count % 30 == 0:
            #     print(f"🎵 Chunk {chunk_count}: Speech probability = {speech_prob:.3f} (threshold: 0.3)")
            
            # Process with VAD
            speech_dict = vad_iterator(audio_16k_float, return_seconds=False)
            
            # Always add original quality audio to buffer if recording
            if is_recording:
                recorded_chunks_original.append(chunk_original)
            
            # Handle VAD events
            if speech_dict:
                if 'start' in speech_dict and not is_recording:
                    print(f"\n🎤 Speech detected! (prob: {speech_prob:.3f})")
                    is_recording = True
                    recorded_chunks_original = [chunk_original]
                
                if 'end' in speech_dict and is_recording:
                    print(f"🔇 Speech ended (prob: {speech_prob:.3f})")
                    is_recording = False
                    transcribe_audio()

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
    sock.close()