"""Main entry point for Game Audio Translator.

Wires together: audio capture -> STT -> translation -> WebSocket broadcast.
"""

import asyncio
import os
import queue

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from audio_capture import create_capture_queue, list_devices
from stt import StreamingTranscriber
from translator import Translator
from ws_server import BroadcastServer


async def feed_audio(audio_q: queue.Queue, transcriber: StreamingTranscriber):
    """Bridge audio capture (thread) to STT (thread). Runs in executor."""
    loop = asyncio.get_event_loop()
    while True:
        chunk = await loop.run_in_executor(None, audio_q.get)
        transcriber.audio_queue.put(chunk)


async def process_results(
    result_queue: asyncio.Queue,
    translator: Translator,
    server: BroadcastServer,
):
    """Translate STT results and broadcast to phones."""
    while True:
        result = await result_queue.get()

        if "partial" in result:
            text_en = result["partial"]
            text_zh = translator.translate(text_en)
            await server.broadcast({
                "type": "partial",
                "text_en": text_en,
                "text_zh": text_zh,
            })
        elif "final" in result:
            text_en = result["final"]
            text_zh = translator.translate(text_en)
            await server.broadcast({
                "type": "final",
                "text_en": text_en,
                "text_zh": text_zh,
            })
            print(f"[EN] {text_en}")
            print(f"[ZH] {text_zh}\n")


async def main():
    device_index = os.getenv("AUDIO_DEVICE_INDEX")
    if device_index is not None:
        device_index = int(device_index)
    ws_port = int(os.getenv("WS_PORT", "8765"))
    http_port = int(os.getenv("HTTP_PORT", "8080"))

    print("=== Game Audio Translator ===\n")
    print("Available audio devices:")
    list_devices()
    print(f"\nPhone UI: http://<your-ip>:{http_port}")
    print(f"WebSocket: ws://<your-ip>:{ws_port}")
    print("\nStarting...")

    # Shared result queue (asyncio.Queue for async consumers)
    result_queue: asyncio.Queue = asyncio.Queue()

    # Callback for STT to deliver results into asyncio world
    loop = asyncio.get_event_loop()

    def on_stt_result(result):
        loop.call_soon_threadsafe(result_queue.put_nowait, result)

    # Start audio capture (auto-detects WASAPI loopback on Windows)
    audio_q, audio_stream = create_capture_queue(device_index)

    # Start STT with reconnection
    transcriber = StreamingTranscriber(language="en-US", on_result=on_stt_result)
    transcriber.start()

    # Start translator
    translator = Translator()

    # Start WebSocket server
    server = BroadcastServer(ws_port=ws_port, http_port=http_port)

    print("\nReady! Waiting for audio...\n")

    try:
        await asyncio.gather(
            server.start_http(),
            server.start_ws(),
            feed_audio(audio_q, transcriber),
            process_results(result_queue, translator, server),
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        audio_stream.stop()
        audio_stream.close()
        transcriber.stop()


if __name__ == "__main__":
    asyncio.run(main())
