"""Google Cloud Translation wrapper.

English to Chinese translation with error handling.
"""

from google.cloud import translate_v2 as translate


class Translator:
    """Translates text from English to Chinese."""

    def __init__(self):
        self.client = translate.Client()

    def translate(self, text: str, source: str = "en", target: str = "zh-CN") -> str:
        """Translate text. Returns original text on failure."""
        if not text or not text.strip():
            return ""
        try:
            result = self.client.translate(
                text, source_language=source, target_language=target
            )
            return result["translatedText"]
        except Exception as e:
            print(f"[Translate] Error: {e}")
            return text
