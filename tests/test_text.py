import base64
import os
import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from twilio.request_validator import RequestValidator

import pytest

from translatron.text import TranslatronText
from translatron.record import TextRecord
from translatron.translator import Translator
from translatron.actions import ActionBase


class MockTranslator(Translator):
    """Mock translator for testing."""

    def __init__(self, detected_lang="en", translations=None):
        self.detected_lang = detected_lang
        self.translations = translations or {}

    def detect_language(self, text: str) -> str:
        return self.detected_lang

    def translate(
        self, text: str, target_language: str, detected_language=None
    ) -> str:
        return self.translations.get(
            target_language, f"[{target_language}] {text}"
        )


class MockAction(ActionBase):
    """Mock action that records calls."""

    def __init__(self):
        self.called_with = []

    def __call__(self, record: TextRecord) -> None:
        self.called_with.append(record)


class MockTranslatronText(TranslatronText):
    """Mock TranslatronText for testing conversation ID override."""
    def _get_conversation_id(self, event: Dict[str, Any]) -> str:
        return event.get("From", [""])[0] + "_custom"


class TestTranslatronText:
    def setup_method(self):
        self.mock_translator = MockTranslator()
        self.mock_action1 = MockAction()
        self.mock_action2 = MockAction()
        self.languages = ["en", "es", "fr"]

        self.translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1, self.mock_action2],
            languages=self.languages,
        )

    def test_initialization(self):
        assert self.translatron.translator == self.mock_translator
        assert self.translatron.actions == [
            self.mock_action1,
            self.mock_action2,
        ]
        assert self.translatron.languages == self.languages

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("test_token_123", "test_token_123"),
            (None, ""),
        ],
    )
    def test_get_twilio_auth_token(self, env_value, expected):
        env_dict = (
            {"TWILIO_AUTH_TOKEN": env_value} if env_value is not None else {}
        )
        clear_env = env_value is None

        with patch.dict(os.environ, env_dict, clear=clear_env):
            token = self.translatron.get_twilio_auth_token()
            assert token == expected

    @pytest.mark.parametrize(
        "body_data,is_base64",
        [
            (
                {
                    "From": "+15551234567",
                    "To": "+15559876543",
                    "Body": "Hello world",
                },
                False,
            ),
            (
                {
                    "From": "+15551234567",
                    "To": "+15559876543",
                    "Body": "Hello world",
                },
                True,
            ),
        ],
    )
    def test_parse_event_params_with_encoded_body(self, body_data, is_base64):
        if is_base64:
            body_str = urlencode(body_data)
            event_body = base64.b64encode(body_str.encode()).decode()
        else:
            event_body = urlencode(body_data)

        event = {"body": event_body, "isBase64Encoded": is_base64}

        result = self.translatron.parse_event_params(event)

        assert result["From"] == ["+15551234567"]
        assert result["To"] == ["+15559876543"]
        assert result["Body"] == ["Hello world"]

    def test_parse_event_params_with_missing_body(self):
        event = {"isBase64Encoded": False}

        result = self.translatron.parse_event_params(event)
        assert result == {}

    def test_parse_event_params_with_unicode_text(self):
        body_data = {
            "From": "+15551234567",
            "To": "+15559876543",
            "Body": "Hello 世界 🌍",
        }
        event = {
            "body": urlencode(body_data, encoding="utf-8"),
            "isBase64Encoded": False,
        }

        result = self.translatron.parse_event_params(event)
        assert result["Body"] == ["Hello 世界 🌍"]

    def test_parse_event_params_malformed_base64_body(self):
        event = {"body": "invalid-base64!@#", "isBase64Encoded": True}

        with pytest.raises(Exception):
            self.translatron.parse_event_params(event)

    def test_conversation_id_override(self):
        """Test that conversation ID can be overridden by subclassing."""
        mock_translatron = MockTranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1],
            languages=self.languages,
        )
        
        params = {"From": ["+1234567890"], "Body": ["Hello"]}
        url = "https://example.com/"
        auth_token = "test_token_123"
        
        validator = RequestValidator(auth_token)
        signature = validator.compute_signature(url, {k: v[0] for k, v in params.items()})
        
        event = {
            "body": urlencode({k: v[0] for k, v in params.items()}),
            "isBase64Encoded": False,
            "headers": {
                "host": "example.com",
                "x-twilio-signature": signature,
            },
        }
        
        with (
            patch("translatron.text.uuid.uuid4") as mock_uuid,
            patch("translatron.text.datetime") as mock_datetime,
            patch.object(
                mock_translatron, "get_twilio_auth_token", return_value=auth_token
            ),
        ):
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="test-uuid-123")
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"
            
            mock_translatron(event, {})
            
            assert len(self.mock_action1.called_with) == 1
            record = self.mock_action1.called_with[0]
            assert record.conversation_id == "+1234567890_custom"

    @pytest.mark.parametrize(
        "auth_token,expected_result",
        [
            ("test_token_123", True),
            ("wrong_token_456", False),
        ],
    )
    def test_validate_twilio_event_signature_validation(
        self, auth_token, expected_result
    ):
        # Ensure parameters are strings, not lists
        params = {"From": "+1234567890", "Body": "Hello"}
        url = "https://example.com/"
        
        validator = RequestValidator(auth_token)
        signature = validator.compute_signature(url, params)
        
        headers = {
            "host": "example.com",
            "x-twilio-signature": signature if expected_result else "invalid_signature",
        }

        # Convert params to list format for internal handling
        list_params = {k: [v] for k, v in params.items()}

        with patch.object(
            self.translatron, "get_twilio_auth_token", return_value="test_token_123"
        ):
            result = self.translatron.validate_twilio_event(list_params, headers)

        assert result is expected_result

    def test_validate_twilio_event_missing_signature_header(self):
        params = {"From": "+1234567890", "Body": "Hello"}
        list_params = {k: [v] for k, v in params.items()}
        headers = {"host": "example.com"}

        with patch.object(
            self.translatron, "get_twilio_auth_token", return_value="test_token"
        ):
            with patch(
                "translatron.text.RequestValidator"
            ) as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate.return_value = False
                mock_validator_class.return_value = mock_validator

                with pytest.raises(KeyError):
                    self.translatron.validate_twilio_event(list_params, headers)

    @patch("translatron.text.uuid.uuid4")
    @patch("translatron.text.datetime")
    def test_get_message_details(self, mock_datetime, mock_uuid):
        mock_uuid.return_value = Mock(spec=uuid.UUID)
        mock_uuid.return_value.__str__ = Mock(return_value="test-uuid-123")
        mock_datetime.datetime.now.return_value.isoformat.return_value = (
            "2023-01-01T12:00:00"
        )

        params = {
            "From": ["+1234567890"],
            "To": ["+0987654321"],
            "Body": ["Hello world"],
        }

        result = self.translatron.get_message_details(params)

        expected = {
            "message_id": "test-uuid-123",
            "conversation_id": "+1234567890",
            "sender": "+1234567890",
            "recipient": "+0987654321",
            "text": "Hello world",
            "timestamp": "2023-01-01T12:00:00Z",
        }
        assert result == expected

    def test_get_message_details_with_missing_fields(self):
        params = {}

        with patch("translatron.text.uuid.uuid4") as mock_uuid:
            with patch("translatron.text.datetime") as mock_datetime:
                mock_uuid.return_value = Mock(spec=uuid.UUID)
                mock_uuid.return_value.__str__ = Mock(
                    return_value="test-uuid-123"
                )
                mock_datetime.datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"

                result = self.translatron.get_message_details(params)

        expected = {
            "message_id": "test-uuid-123",
            "conversation_id": "",
            "sender": "",
            "recipient": "",
            "text": "",
            "timestamp": "2023-01-01T12:00:00Z",
        }
        assert result == expected

    def test_get_conversation_id_method(self):
        event = {"From": ["+15551234567"]}
        result = self.translatron._get_conversation_id(event)
        assert result == "+15551234567"

    def test_detect_and_translate_with_translations(self):
        self.mock_translator.detected_lang = "en"
        self.mock_translator.translations = {
            "es": "Hola mundo",
            "fr": "Bonjour le monde",
        }

        message = {"text": "Hello world", "sender": "+15551234567"}

        translations, original_lang = self.translatron.detect_and_translate(
            message
        )

        assert original_lang == "en"
        assert len(translations) == 2

        translation_dict = {t["lang"]: t["text"] for t in translations}
        assert translation_dict["es"] == "Hola mundo"
        assert translation_dict["fr"] == "Bonjour le monde"

    def test_detect_and_translate_skip_same_language(self):
        self.mock_translator.detected_lang = "es"
        self.mock_translator.translations = {
            "en": "Hello world",
            "fr": "Bonjour le monde",
        }

        message = {"text": "Hola mundo", "sender": "+15551234567"}

        translations, original_lang = self.translatron.detect_and_translate(
            message
        )

        assert original_lang == "es"
        assert len(translations) == 2  # Should skip 'es' translation

        translation_langs = [t["lang"] for t in translations]
        assert "es" not in translation_langs
        assert "en" in translation_langs
        assert "fr" in translation_langs

    def test_detect_and_translate_source_language_not_in_targets(self):
        self.mock_translator.detected_lang = "zh"

        message = {"text": "你好世界", "sender": "+15551234567"}

        translations, original_lang = self.translatron.detect_and_translate(
            message
        )

        assert original_lang == "zh"
        assert (
            len(translations) == 3
        )  # Should translate to all target languages

    def test_detect_and_translate_with_empty_text(self):
        message = {"text": "", "sender": "+15559876543"}

        translations, original_lang = self.translatron.detect_and_translate(
            message
        )

        assert isinstance(original_lang, str)
        assert isinstance(translations, list)

    def test_action_calls_all_actions(self):
        basic_text_record = TextRecord(
            message_id="test-id",
            conversation_id="test-conv",
            sender="+1234567890",
            recipient="+0987654321",
            original_lang="en",
            original_text="Hello",
            translations=[],
            timestamp="2023-01-01T12:00:00Z",
        )
        self.translatron.action(basic_text_record)

        assert len(self.mock_action1.called_with) == 1
        assert len(self.mock_action2.called_with) == 1
        assert self.mock_action1.called_with[0] == basic_text_record
        assert self.mock_action2.called_with[0] == basic_text_record

    def test_build_response(self):
        response = self.translatron.build_response()

        assert response["statusCode"] == 200
        assert response["body"] == "<Response></Response>"
        assert response["headers"]["Content-Type"] == "application/xml"

    def test_full_call_flow_with_valid_signature(self):
        self.mock_translator.detected_lang = "en"
        self.mock_translator.translations = {
            "es": "Hola mundo",
            "fr": "Bonjour le monde",
        }

        auth_token = "test_token_123"
        body_data = {
            "From": ["+15551234567"],
            "To": ["+15559876543"],
            "Body": ["Hello world"],
        }
        url = "https://example.com/"
        
        validator = RequestValidator(auth_token)
        signature = validator.compute_signature(url, {k: v[0] for k, v in body_data.items()})
        
        event = {
            "body": urlencode({k: v[0] for k, v in body_data.items()}),
            "isBase64Encoded": False,
            "headers": {
                "host": "example.com",
                "x-twilio-signature": signature,
            },
        }
        context = {}

        with (
            patch("translatron.text.uuid.uuid4") as mock_uuid,
            patch("translatron.text.datetime") as mock_datetime,
            patch.object(
                self.translatron, "get_twilio_auth_token", return_value=auth_token
            ),
        ):
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="full-flow-id")
            mock_datetime.datetime.now.return_value.isoformat.return_value = (
                "2023-01-01T15:00:00"
            )

            response = self.translatron(event, context)

            assert response["statusCode"] == 200
            assert response["body"] == "<Response></Response>"

            assert len(self.mock_action1.called_with) == 1
            assert len(self.mock_action2.called_with) == 1

            record = self.mock_action1.called_with[0]
            assert record.message_id == "full-flow-id"
            assert record.sender == "+15551234567"
            assert record.recipient == "+15559876543"
            assert record.original_text == "Hello world"
            assert record.original_lang == "en"
            assert len(record.translations) == 2

    def test_full_call_flow_with_invalid_signature_returns_403(self):
        auth_token = "test_token_123"
        body_data = {
            "From": ["+15551234567"],
            "To": ["+15559876543"],
            "Body": ["Hello world"],
        }
        url = "https://example.com/"
        
        validator = RequestValidator("wrong_token_456")
        signature = validator.compute_signature(url, {k: v[0] for k, v in body_data.items()})
        
        event = {
            "body": urlencode({k: v[0] for k, v in body_data.items()}),
            "isBase64Encoded": False,
            "headers": {
                "host": "example.com",
                "x-twilio-signature": signature,
            },
        }

        with patch.object(
            self.translatron, "get_twilio_auth_token", return_value=auth_token
        ):
            response = self.translatron(event, {})

            assert response["statusCode"] == 403
            assert (
                response["body"]
                == "Forbidden: Invalid Twilio request signature"
            )

            assert len(self.mock_action1.called_with) == 0
            assert len(self.mock_action2.called_with) == 0

    def test_call_with_logging(self):
        body_data = {
            "From": ["+15551234567"],
            "To": ["+15559876543"],
            "Body": ["Test logging"],
        }
        event = {
            "body": urlencode({k: v[0] for k, v in body_data.items()}),
            "isBase64Encoded": False,
            "headers": {
                "host": "example.com",
                "x-twilio-signature": "valid_signature",
            },
        }

        with (
            patch("translatron.text.logger") as mock_logger,
            patch("translatron.text.uuid.uuid4") as mock_uuid,
            patch("translatron.text.datetime") as mock_datetime,
            patch.object(
                self.translatron, "validate_twilio_event", return_value=True
            ),
        ):
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(
                return_value="logging-test-id"
            )
            mock_datetime.datetime.now.return_value.isoformat.return_value = (
                "2023-01-01T16:00:00"
            )

            self.translatron(event, {})

            mock_logger.info.assert_any_call(
                "Received SMS from %s", "+15551234567"
            )
            mock_logger.info.assert_any_call(
                "Received SMS to %s", "+15559876543"
            )
            mock_logger.info.assert_any_call("SMS text: %s", "Test logging")

    def test_empty_languages_list(self):
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1],
            languages=[],
        )

        message = {"text": "Hello", "sender": "+15559876543"}
        translations, original_lang = translatron.detect_and_translate(message)

        assert original_lang == "en"
        assert len(translations) == 0

    def test_single_language_same_as_detected(self):
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1],
            languages=["en"],
        )

        self.mock_translator.detected_lang = "en"

        message = {"text": "Hello", "sender": "+15559876543"}
        translations, original_lang = translatron.detect_and_translate(message)

        assert original_lang == "en"
        assert len(translations) == 0

    def test_real_test_event_signature_validation(self):
        # Create a test event using the Twilio validator directly
        url = "https://example.com/"
        param_dict = {
            "From": ["+1234567890"],
            "To": ["+0987654321"],
            "Body": ["Hello world"],
        }
        
        # Get the auth token from environment
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not auth_token:
            pytest.skip("TWILIO_AUTH_TOKEN environment variable not set")
        
        validator = RequestValidator(auth_token)
        signature = validator.compute_signature(url, {k: v[0] for k, v in param_dict.items()})
        
        event = {
            "body": urlencode({k: v[0] for k, v in param_dict.items()}),
            "isBase64Encoded": False,
            "headers": {
                "host": "example.com",
                "x-twilio-signature": signature,
                "content-type": "application/x-www-form-urlencoded",
            },
            "httpMethod": "POST"
        }

        with patch("translatron.text.uuid.uuid4") as mock_uuid:
            with patch("translatron.text.datetime") as mock_datetime:
                mock_uuid.return_value = Mock(spec=uuid.UUID)
                mock_uuid.return_value.__str__ = Mock(
                    return_value="test-uuid-123"
                )
                mock_datetime.datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"

                response = self.translatron(event, {})

        assert response["statusCode"] == 200
        assert len(self.mock_action1.called_with) == 1

        record = self.mock_action1.called_with[0]
        assert record.sender == "+1234567890"
        assert record.recipient == "+0987654321"
        assert record.original_text == "Hello world"
