from abc import ABC, abstractmethod
from typing import Optional, Any


class Translator(ABC):
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Return ISO language code for the input text."""
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        target_language: str,
        detected_language: Optional[str] = None,
    ) -> str:
        """Return translated text into target_language."""
        pass


class NonTranslator(Translator):
    def detect_language(self, text: str) -> str:
        """Return 'en' for English as a default."""
        return "en"

    def translate(
        self,
        text: str,
        target_language: str,
        detected_language: Optional[str] = None,
    ) -> str:
        """Return the original text as no translation is performed."""
        return text


class AmazonTranslator(Translator):
    def __init__(self):
        import boto3

        self.translate_client = boto3.client("translate")
        self.comprehend_client = boto3.client("comprehend")

    def detect_language(self, text: str) -> str:
        resp = self.comprehend_client.detect_dominant_language(Text=text)
        return resp["Languages"][0]["LanguageCode"]

    def translate(
        self,
        text: str,
        target_language: str,
        detected_language: Optional[str] = None,
    ) -> str:
        if detected_language is None:
            detected_language = "auto"
        resp = self.translate_client.translate_text(
            Text=text,
            SourceLanguageCode=detected_language,
            TargetLanguageCode=target_language,
        )
        return resp["TranslatedText"]


class GoogleTranslator(Translator):
    def __init__(self, credentials_path: str):
        # require GOOGLE_APPLICATION_CREDENTIALS env var
        from google.cloud import translate_v2 as translate

        # Note: credentials_path parameter is not used - Google client uses
        # GOOGLE_APPLICATION_CREDENTIALS env var
        self.client: Any = translate.Client()

    def detect_language(self, text: str) -> str:
        resp = self.client.detect_language(text)
        return resp["language"]

    def translate(
        self,
        text: str,
        target_language: str,
        detected_language: Optional[str] = None,
    ) -> str:
        # Google Translate API can optionally use source language hint
        if detected_language and detected_language != "auto":
            resp = self.client.translate(
                text,
                target_language=target_language,
                source_language=detected_language,
            )
        else:
            resp = self.client.translate(text, target_language=target_language)
        return resp["translatedText"]
