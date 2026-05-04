"""Test audio capture: records 5 seconds from default input, saves as WAV.

Usage:
    python test/test_audio_capture.py
"""

import sys
import os
import time
import queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from audio_capture import create_capture_queue, list_devices, SAMPLE_RATE, CHANNELS


def main():
    print("Available audio devices:\n")
    list_devices()

    device_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(f"\nRecording 5 seconds from device {device_index}...")
    print("(Speak into your microphone or play some audio)\n")

    audio_q, stream = create_capture_queue(device_index)
    chunks = []

    start = time.time()
    while time.time() - start < 5:
        try:
            chunk = audio_q.get(timeout=0.5)
            chunks.append(chunk)
        except queue.Empty:
            pass

    stream.stop()
    stream.close()

    output_path = os.path.join(os.path.dirname(__file__), "test_output.wav")
    import wave
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(chunks))

    duration = len(b"".join(chunks)) / (SAMPLE_RATE * CHANNELS * 2)
    print(f"Saved {duration:.1f}s audio to {output_path}")
    print("Play it back to verify capture worked.")


if __name__ == "__main__":
    main()
