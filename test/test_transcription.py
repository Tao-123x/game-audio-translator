"""Test Google Cloud STT + Translation pipeline.

Reads a WAV file, sends it to Google Cloud STT streaming,
then translates the result to Chinese.

Usage:
    python test/test_transcription.py [path_to_wav]

Requires:
    - GOOGLE_APPLICATION_CREDENTIALS set in .env
    - Cloud Speech-to-Text API enabled
    - Cloud Translation API enabled
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from google.cloud import speech
from translator import Translator


def transcribe_file(wav_path: str):
    """Transcribes a WAV file using Google Cloud STT streaming."""
    client = speech.SpeechClient()

    with open(wav_path, "rb") as f:
        content = f.read()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    def request_generator():
        yield speech.StreamingRecognizeRequest(
            streaming_config=streaming_config
        )
        # Send audio in 32KB chunks
        chunk_size = 32000
        for i in range(0, len(content), chunk_size):
            yield speech.StreamingRecognizeRequest(
                audio_content=content[i:i + chunk_size]
            )

    responses = client.streaming_recognize(request_generator())

    final_transcript = ""
    for response in responses:
        for result in response.results:
            text = result.alternatives[0].transcript
            if result.is_final:
                final_transcript = text
                print(f"[FINAL] {text}")
            else:
                print(f"[PARTIAL] {text}", end="\r")

    return final_transcript


def main():
    wav_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "test_output.wav"
    )

    if not os.path.exists(wav_path):
        print(f"WAV file not found: {wav_path}")
        print("Run test_audio_capture.py first to create test_output.wav")
        sys.exit(1)

    print(f"Transcribing: {wav_path}\n")
    transcript = transcribe_file(wav_path)

    if not transcript:
        print("\nNo speech detected. Make sure the WAV contains English speech.")
        sys.exit(1)

    print(f"\nTranslating to Chinese...")
    translator = Translator()
    zh = translator.translate(transcript)
    print(f"[ZH] {zh}")


if __name__ == "__main__":
    main()
