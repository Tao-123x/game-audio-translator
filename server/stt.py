"""Google Cloud Speech-to-Text streaming recognition.

Takes PCM audio chunks from a queue, streams them to Google Cloud STT,
and delivers partial/final transcript results via a callback.

Automatically reconnects on stream failures with exponential backoff.
"""

import queue
import time
from google.cloud import speech


MAX_RECONNECT_DELAY = 30  # seconds


class StreamingTranscriber:
    """Manages a streaming STT session with automatic reconnection.

    Args:
        language: BCP-47 language code (e.g. "en-US").
        on_result: Callback called with {"partial": str} or {"final": str}.
                   Called from a background thread.
    """

    def __init__(self, language: str = "en-US", on_result=None):
        self.language = language
        self.on_result = on_result
        self.client = speech.SpeechClient()
        self.audio_queue: queue.Queue = queue.Queue()
        self._running = False

    def _build_config(self):
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self.language,
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        return streaming_config

    def _request_generator(self):
        """Yields streaming recognize requests from the audio queue."""
        streaming_config = self._build_config()
        yield speech.StreamingRecognizeRequest(
            streaming_config=streaming_config
        )
        while self._running:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except queue.Empty:
                continue

    def _deliver(self, result):
        """Deliver a result via callback."""
        if self.on_result:
            self.on_result(result)

    def _run_stream(self):
        """Run a single streaming session. Raises on connection failure."""
        requests = self._request_generator()
        responses = self.client.streaming_recognize(requests=requests)

        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            transcript = result.alternatives[0].transcript
            if result.is_final:
                self._deliver({"final": transcript})
            else:
                self._deliver({"partial": transcript})

    def _run(self):
        """Runs the streaming recognition loop with reconnection."""
        delay = 1
        while self._running:
            try:
                self._run_stream()
                # Stream ended cleanly (server closed it)
                if self._running:
                    print("[STT] Stream ended, reconnecting...")
                    time.sleep(1)
                    delay = 1
            except Exception as e:
                if not self._running:
                    break
                print(f"[STT] Error: {e}, retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_DELAY)

    def start(self):
        """Start the streaming recognition in a background thread."""
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the streaming recognition."""
        self._running = False
        self._thread.join(timeout=5)
