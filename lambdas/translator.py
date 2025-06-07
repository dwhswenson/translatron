from abc import ABC, abstractmethod

class Translator(ABC):
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Return ISO language code for the input text."""
        pass

    @abstractmethod
    def translate(self, text: str, target_language: str) -> str:
        """Return translated text into target_language."""
        pass


class AmazonTranslator(Translator):
    def __init__(self):
        import boto3
        self.translate_client = boto3.client("translate")
        self.comprehend_client = boto3.client("comprehend")

    def detect_language(self, text: str) -> str:
        resp = self.comprehend_client.detect_dominant_language(Text=text)
        return resp["Languages"][0]["LanguageCode"]

    def translate(self, text: str, target_language: str,
                  detected_language: str = None) -> str:
        if detected_language is None:
            detected_language = "auto"
        resp = self.translate_client.translate_text(
            Text=text,
            SourceLanguageCode=detected_language,
            TargetLanguageCode=target_language
        )
        return resp["TranslatedText"]


class GoogleTranslator(Translator):
    def __init__(self, credentials_path: str):
        # require GOOGLE_APPLICATION_CREDENTIALS env var
        from google.cloud import translate_v2 as translate
        import os
        self.client = translate.Client()

    def detect_language(self, text: str) -> str:
        resp = self.client.detect_language(text)
        return resp["language"]

    def translate(self, text: str, target_language: str) -> str:
        resp = self.client.translate(text, target_language=target_language)
        return resp["translatedText"]
