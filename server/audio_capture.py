"""System audio capture using sounddevice.

Captures PCM16 mono 16kHz audio and puts chunks into a thread-safe queue.
On macOS: captures from default input device (mic) for development.
On Windows: capture from VoiceMeeter output device for game audio.
"""

import queue
import sounddevice as sd
import numpy as np


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_MS = 200  # 200ms per chunk
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 3200 frames


def list_devices():
    """Print all available audio devices with their indices."""
    print(sd.query_devices())


def create_capture_queue(device_index: int = 0) -> queue.Queue:
    """Create an audio capture stream and return the queue of audio chunks.

    Args:
        device_index: Audio device index. Use 0 for default input on macOS.
            On Windows, use the VoiceMeeter output device index.

    Returns:
        A queue.Queue that receives raw PCM16 bytes (mono 16kHz).
    """
    audio_queue: queue.Queue = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(f"Audio capture status: {status}")
        # Convert float32 [-1, 1] to int16 PCM
        pcm_data = (indata[:, 0] * 32767).astype(np.int16)
        audio_queue.put(pcm_data.tobytes())

    stream = sd.InputStream(
        device=device_index,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=CHUNK_SIZE,
        callback=callback,
    )
    stream.start()

    return audio_queue, stream


if __name__ == "__main__":
    print("Available audio devices:")
    list_devices()
    print(f"\nCapturing 5 seconds of audio from device 0...")
    audio_queue, stream = create_capture_queue(0)
    import time
    chunks = []
    start = time.time()
    while time.time() - start < 5:
        try:
            chunk = audio_queue.get(timeout=0.5)
            chunks.append(chunk)
        except queue.Empty:
            pass
    stream.stop()
    stream.close()
    # Save to WAV for verification
    import wave
    with wave.open("test_output.wav", "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(chunks))
    print(f"Saved {len(chunks)} chunks to test_output.wav")
