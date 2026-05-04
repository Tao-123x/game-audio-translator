"""Main entry point for Game Audio Translator.

Wires together: audio capture → STT → translation → WebSocket broadcast.
"""

import asyncio
import os
import sys
import queue

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from audio_capture import create_capture_queue, list_devices
from stt import StreamingTranscriber
from translator import Translator
from ws_server import BroadcastServer


async def main():
    device_index = int(os.getenv("AUDIO_DEVICE_INDEX", "0"))
    ws_port = int(os.getenv("WS_PORT", "8765"))
    http_port = int(os.getenv("HTTP_PORT", "8080"))

    print("=== Game Audio Translator ===\n")
    print("Available audio devices:")
    list_devices()
    print(f"\nUsing device index: {device_index}")
    print(f"Phone UI: http://<your-ip>:{http_port}")
    print(f"WebSocket: ws://<your-ip>:{ws_port}")
    print("\nStarting...")

    # Start audio capture
    audio_q, audio_stream = create_capture_queue(device_index)

    # Start STT
    transcriber = StreamingTranscriber(language="en-US")
    transcriber.start()

    # Start translator
    translator = Translator()

    # Start WebSocket server
    server = BroadcastServer(ws_port=ws_port, http_port=http_port)

    # Run HTTP and WS servers concurrently
    http_task = asyncio.create_task(server.start_http())
    ws_task = asyncio.create_task(server.start_ws())

    print("\nReady! Waiting for audio...\n")

    loop = asyncio.get_event_loop()

    try:
        while True:
            # Feed audio chunks to STT (non-blocking via executor)
            try:
                chunk = await loop.run_in_executor(None, audio_q.get)
                transcriber.audio_queue.put(chunk)
            except queue.Empty:
                pass

            # Check for STT results
            try:
                result = transcriber.result_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            # Process STT result
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

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        audio_stream.stop()
        audio_stream.close()
        transcriber.stop()


if __name__ == "__main__":
    asyncio.run(main())
