"""System audio capture using sounddevice.

Captures PCM16 mono 16kHz audio and puts chunks into a thread-safe queue.

Windows: WASAPI loopback capture (no VoiceMeeter needed).
macOS/Linux: default input device (mic) for development.
"""

import queue
import sys
import sounddevice as sd
import numpy as np


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_MS = 200  # 200ms per chunk
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 3200 frames


def _find_wasapi_host_api():
    """Find the WASAPI host API index. Returns None if not available."""
    for i, api in enumerate(sd.query_hostapis()):
        if "WASAPI" in api["name"]:
            return i, api
    return None, None


def find_wasapi_loopback_device():
    """Find the default WASAPI output device for loopback capture.

    Returns:
        (device_index, device_name) or (None, None) if not available.
    """
    api_idx, api_info = _find_wasapi_host_api()
    if api_info is None:
        return None, None

    out_idx = api_info["defaultOutputDevice"]
    if out_idx < 0:
        return None, None

    device = sd.query_devices(out_idx)
    return out_idx, device["name"]


def list_devices():
    """Print all available audio devices with their indices."""
    print(sd.query_devices())
    if sys.platform == "win32":
        loopback_idx, loopback_name = find_wasapi_loopback_device()
        if loopback_idx is not None:
            print(f"\nWASAPI loopback device: [{loopback_idx}] {loopback_name}")
        else:
            print("\nWASAPI loopback not available.")


def create_capture_queue(device_index: int = None) -> tuple[queue.Queue, sd.InputStream]:
    """Create an audio capture stream and return the queue of audio chunks.

    On Windows: automatically uses WASAPI loopback to capture system audio.
    On macOS/Linux: uses the specified device (default: 0, i.e. mic).

    Args:
        device_index: Audio device index. If None, auto-detects on Windows
            (WASAPI loopback from default output) or uses 0 on other platforms.

    Returns:
        (audio_queue, stream) - queue receives raw PCM16 bytes (mono 16kHz).
    """
    extra_settings = None

    if sys.platform == "win32" and device_index is None:
        loopback_idx, loopback_name = find_wasapi_loopback_device()
        if loopback_idx is not None:
            device_index = loopback_idx
            extra_settings = sd.WasapiSettings(loopback=True)
            print(f"Using WASAPI loopback: [{loopback_idx}] {loopback_name}")
        else:
            print("WARNING: WASAPI loopback not available, falling back to default input.")
            device_index = 0
    elif device_index is None:
        device_index = 0

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
        extra_settings=extra_settings,
    )
    stream.start()

    return audio_queue, stream


if __name__ == "__main__":
    print("Available audio devices:")
    list_devices()
    print(f"\nCapturing 5 seconds of audio...")
    audio_queue, stream = create_capture_queue()
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
