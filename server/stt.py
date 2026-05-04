"""Google Cloud Speech-to-Text streaming recognition.

Takes PCM audio chunks from a queue, streams them to Google Cloud STT,
and yields partial/final transcript results.
"""

import queue
from google.cloud import speech


class StreamingTranscriber:
    """Manages a streaming STT session.

    Usage:
        transcriber = StreamingTranscriber()
        transcriber.start()
        # Feed audio chunks via transcriber.audio_queue
        # Read results via transcriber.result_queue
        # Each result is {"partial": str} or {"final": str}
        transcriber.stop()
    """

    def __init__(self, language: str = "en-US"):
        self.language = language
        self.client = speech.SpeechClient()
        self.audio_queue: queue.Queue = queue.Queue()
        self.result_queue: queue.Queue = queue.Queue()
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
        # First request carries config
        yield speech.StreamingRecognizeRequest(
            streaming_config=streaming_config
        )
        # Subsequent requests carry audio chunks
        while self._running:
            try:
                chunk = self.audio_queue.get(timeout=0.5)
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
            except queue.Empty:
                continue

    def _run(self):
        """Runs the streaming recognition loop."""
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
                self.result_queue.put({"final": transcript})
            else:
                self.result_queue.put({"partial": transcript})

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
