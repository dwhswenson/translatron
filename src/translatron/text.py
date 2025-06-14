# src/translatron/text.py
import base64
import datetime
import logging
import os
import uuid
from typing import List, Dict, Any, Tuple
from urllib.parse import parse_qs
from twilio.request_validator import RequestValidator

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
        params = self.parse_event_params(event)
        headers = event["headers"]
        if not self.validate_twilio_event(params, headers):
            logger.error("Invalid Twilio request signature")
            return {
                "statusCode": 403,
                "body": "Forbidden: Invalid Twilio request signature",
            }
        message = self.get_message_details(params)
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

    def get_twilio_auth_token(self) -> str:
        return os.getenv("TWILIO_AUTH_TOKEN", "")

    def parse_event_params(self, event: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract and parse parameters from the event body."""
        body_str = event.get("body", "")
        if event.get("isBase64Encoded", False):
            body_str = base64.b64decode(body_str).decode("utf-8")

        logger.debug("Body string: %s", body_str)
        params = parse_qs(body_str, keep_blank_values=True)
        return params

    def validate_twilio_event(self, params, headers) -> bool:
        auth_token = self.get_twilio_auth_token()
        validator = RequestValidator(auth_token)

        host = headers.get("host")
        if not host:
            logger.error("Missing 'host' header in request")
            return False

        url = f"https://{host}/"  # for lambdas, this will be correct
        tw_sig = headers["x-twilio-signature"]

        validator_params = {k: v[0] for k, v in params.items()}
        logger.debug("Validating Twilio request with URL: %s", url)
        logger.debug("Twilio signature: %s", tw_sig)
        logger.debug("Validator parameters: %s", validator_params)

        is_valid = validator.validate(url, validator_params, tw_sig)
        return is_valid

    def get_message_details(
        self, params: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        sender = params.get("From", [""])[0]
        logger.info("Received SMS from %s", sender)
        recipient = params.get("To", [""])[0]
        logger.info("Received SMS to %s", recipient)
        text = params.get("Body", [""])[0]
        logger.info("SMS text: %s", text)
        timestamp = (
            datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        )
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
