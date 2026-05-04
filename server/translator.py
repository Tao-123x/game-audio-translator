"""Google Cloud Translation wrapper.

Simple English to Chinese translation.
"""

from google.cloud import translate_v2 as translate


class Translator:
    """Translates text from English to Chinese."""

    def __init__(self):
        self.client = translate.Client()

    def translate(self, text: str, source: str = "en", target: str = "zh-CN") -> str:
        """Translate text.

        Args:
            text: Source text to translate.
            source: Source language code.
            target: Target language code.

        Returns:
            Translated text string.
        """
        result = self.client.translate(text, source_language=source, target_language=target)
        return result["translatedText"]
