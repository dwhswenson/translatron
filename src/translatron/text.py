# src/translatron/text.py
import base64
import datetime
import logging
import uuid
from typing import List, Dict, Any, Tuple
from urllib.parse import parse_qs

from .record import TextRecord
from .translator import Translator
from .actions import ActionBase

logger = logging.getLogger(__name__)


class TranslatronText:  # TODO: make this an ABC
    """Reusable Twilio‑>Translate‑>Whatever Lambda core."""

    def __init__(
        self,
        translator: Translator,
        actions: List[ActionBase],
        languages: List[str],
    ) -> None:
        self.translator = translator
        self.actions = actions
        self.languages = languages

    # ---- public entrypoint -------------------------------------------------
    def __call__(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        logger.info("Received event: %s", event)  # TODO: remove in production
        message = self.parse_event(event)
        translations, orig_lang = self.detect_and_translate(message)
        record = TextRecord(
            message_id=message["message_id"],
            conversation_id=message["conversation_id"],
            sender=message["sender"],
            recipient=message["recipient"],
            original_lang=orig_lang,
            original_text=message["text"],
            translations=translations,
            timestamp=message["timestamp"],
        )
        self.action(record)
        return self.build_response()

    # ---- overridable hooks -------------------------------------------------
    def _get_conversation_id(self, event: Dict[str, Any]) -> str:
        """Extract conversation ID from the event."""
        sender = event.get("From", "")
        return sender

    def parse_event(self, event: Dict[str, Any]) -> Dict[str, str]:
        body_str = event.get("body", "")
        if event.get("isBase64Encoded", False):
            body_str = base64.b64decode(body_str).decode("utf-8")

        params = parse_qs(body_str)
        sender = params.get("From", [""])[0]
        logger.info("Received SMS from %s", sender)
        recipient = params.get("To", [""])[0]
        logger.info("Received SMS to %s", recipient)
        text = params.get("Body", [""])[0]
        logger.info("SMS text: %s", text)
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        logger.info("Timestamp: %s", timestamp)

        message_id = str(uuid.uuid4())
        logger.info("Message ID: %s", message_id)
        conversation_id = sender
        logger.info("Conversation ID: %s", conversation_id)

        return {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender": sender,
            "recipient": recipient,
            "text": text,
            "timestamp": timestamp,
        }

    def detect_and_translate(
        self, message: Dict[str, str]
    ) -> Tuple[List[Dict[str, str]], str]:
        """Runs language detection + translations."""
        original_lang = self.translator.detect_language(message["text"])
        logger.info("Detected language: %s", original_lang)
        translations = []
        for target in self.languages:
            if target == original_lang:
                continue
            translated_text = self.translator.translate(
                message["text"], target, detected_language=original_lang
            )
            logger.info("Translated to %s: %s", target, translated_text)
            translations.append({"lang": target, "text": translated_text})

        return translations, original_lang

    def action(self, record: TextRecord) -> None:
        """E.g. forward via Twilio, invoke SNS, push WebSocket…"""
        for action in self.actions:
            action(record)

    def build_response(self) -> Dict[str, Any]:
        """Return the Twilio-compatible XML / HTTP 200."""
        return {
            "statusCode": 200,
            "body": "<Response></Response>",
            "headers": {"Content-Type": "application/xml"},
        }
