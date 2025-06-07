import pytest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from translatron.text import TranslatronText
from translatron.translator import NonTranslator, Translator
from translatron.actions import ActionBase, NullAction
from translatron.record import TextRecord


class MockTranslator(Translator):
    """Mock translator for testing."""
    
    def __init__(self, detected_lang="en", translations=None):
        self.detected_lang = detected_lang
        self.translations = translations or {}
    
    def detect_language(self, text: str) -> str:
        return self.detected_lang
    
    def translate(self, text: str, target_language: str, detected_language=None) -> str:
        return self.translations.get(target_language, f"[{target_language}] {text}")


class MockAction(ActionBase):
    """Mock action that records calls."""
    
    def __init__(self):
        self.called_with = []
    
    def __call__(self, record: TextRecord) -> None:
        self.called_with.append(record)


class TestTranslatronText:
    def setup_method(self):
        self.mock_translator = MockTranslator()
        self.mock_action1 = MockAction()
        self.mock_action2 = MockAction()
        self.languages = ["en", "es", "fr"]
        
        self.translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1, self.mock_action2],
            languages=self.languages
        )

    def test_initialization(self):
        """Test TranslatronText initialization."""
        assert self.translatron.translator == self.mock_translator
        assert self.translatron.actions == [self.mock_action1, self.mock_action2]
        assert self.translatron.languages == self.languages

    def test_parse_event_with_form_data(self, sample_twilio_event):
        """Test parsing a standard Twilio webhook event."""
        event = sample_twilio_event
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='test-message-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T12:00:00'
            
            result = self.translatron.parse_event(event)
            
            assert result['sender'] == '+15551234567'
            assert result['recipient'] == '+15559876543'
            assert result['text'] == 'Hello world'
            assert result['message_id'] == 'test-message-id'
            assert result['conversation_id'] == '+15551234567'
            assert result['timestamp'] == '2023-01-01T12:00:00Z'

    def test_parse_event_with_base64_encoded_body(self, sample_base64_twilio_event):
        """Test parsing event with base64 encoded body."""
        event = sample_base64_twilio_event
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='encoded-message-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T13:00:00'
            
            result = self.translatron.parse_event(event)
            
            assert result['text'] == 'Base64 encoded message'
            assert result['sender'] == '+15551234567'

    def test_parse_event_with_missing_fields(self):
        """Test parsing event with missing optional fields."""
        event = {
            'body': '',
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='missing-fields-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T14:00:00'
            
            result = self.translatron.parse_event(event)
            
            assert result['sender'] == ''
            assert result['recipient'] == ''
            assert result['text'] == ''
            assert result['message_id'] == 'missing-fields-id'

    def test_detect_and_translate_with_translations(self):
        """Test language detection and translation."""
        self.mock_translator.detected_lang = "en"
        self.mock_translator.translations = {
            "es": "Hola mundo",
            "fr": "Bonjour le monde"
        }
        
        message = {
            'text': 'Hello world',
            'sender': '+15551234567'
        }
        
        translations, original_lang = self.translatron.detect_and_translate(message)
        
        assert original_lang == "en"
        assert len(translations) == 2
        
        # Check translations
        translation_dict = {t['lang']: t['text'] for t in translations}
        assert translation_dict['es'] == 'Hola mundo'
        assert translation_dict['fr'] == 'Bonjour le monde'

    def test_detect_and_translate_skip_same_language(self):
        """Test that translation skips target language same as detected language."""
        self.mock_translator.detected_lang = "es"
        self.mock_translator.translations = {
            "en": "Hello world",
            "fr": "Bonjour le monde"
        }
        
        message = {
            'text': 'Hola mundo',
            'sender': '+15551234567'
        }
        
        translations, original_lang = self.translatron.detect_and_translate(message)
        
        assert original_lang == "es"
        assert len(translations) == 2  # Should skip 'es' translation
        
        # Check that Spanish is not in translations
        translation_langs = [t['lang'] for t in translations]
        assert 'es' not in translation_langs
        assert 'en' in translation_langs
        assert 'fr' in translation_langs

    def test_detect_and_translate_no_translations_needed(self):
        """Test when detected language is not in target languages."""
        self.mock_translator.detected_lang = "zh"  # Chinese, not in self.languages
        
        message = {
            'text': '你好世界',
            'sender': '+15551234567'
        }
        
        translations, original_lang = self.translatron.detect_and_translate(message)
        
        assert original_lang == "zh"
        assert len(translations) == 3  # Should translate to all target languages

    def test_action_calls_all_actions(self, basic_text_record):
        """Test that action method calls all configured actions."""
        # basic_text_record is fine as-is for this test
        self.translatron.action(basic_text_record)
        
        # Both actions should have been called
        assert len(self.mock_action1.called_with) == 1
        assert len(self.mock_action2.called_with) == 1
        assert self.mock_action1.called_with[0] == basic_text_record
        assert self.mock_action2.called_with[0] == basic_text_record

    def test_build_response(self):
        """Test building Twilio-compatible response."""
        response = self.translatron.build_response()
        
        assert response['statusCode'] == 200
        assert response['body'] == '<Response></Response>'
        assert response['headers']['Content-Type'] == 'application/xml'

    def test_full_call_flow(self):
        """Test the complete __call__ flow end-to-end."""
        # Setup
        self.mock_translator.detected_lang = "en"
        self.mock_translator.translations = {
            "es": "Hola mundo",
            "fr": "Bonjour le monde"
        }
        
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Hello world'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        context = {}  # Mock context
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='full-flow-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T15:00:00'
            
            response = self.translatron(event, context)
            
            # Check response
            assert response['statusCode'] == 200
            assert response['body'] == '<Response></Response>'
            
            # Check that actions were called
            assert len(self.mock_action1.called_with) == 1
            assert len(self.mock_action2.called_with) == 1
            
            # Verify the record passed to actions
            record = self.mock_action1.called_with[0]
            assert record.message_id == 'full-flow-id'
            assert record.sender == '+15551234567'
            assert record.recipient == '+15559876543'
            assert record.original_text == 'Hello world'
            assert record.original_lang == 'en'
            assert len(record.translations) == 2

    def test_call_with_logging(self):
        """Test that appropriate logging occurs during call."""
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Test logging'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.logger') as mock_logger, \
             patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='logging-test-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T16:00:00'
            
            self.translatron(event, {})
            
            # Check that info logging calls were made
            mock_logger.info.assert_any_call("Received SMS from %s", '+15551234567')
            mock_logger.info.assert_any_call("Received SMS to %s", '+15559876543')
            mock_logger.info.assert_any_call("SMS text: %s", 'Test logging')

    def test_call_with_translator_error(self):
        """Test handling when translator raises an error."""
        # Make translator raise an exception
        self.mock_translator.detect_language = Mock(side_effect=Exception("Translation API Error"))
        
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'This will fail'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='error-test-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T17:00:00'
            
            # Should propagate the exception
            with pytest.raises(Exception, match="Translation API Error"):
                self.translatron(event, {})

    def test_call_with_action_error(self):
        """Test handling when an action raises an error."""
        # Make one action raise an exception
        error_action = Mock(side_effect=Exception("Action Error"))
        
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1, error_action, self.mock_action2],
            languages=self.languages
        )
        
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Action will fail'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='action-error-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T18:00:00'
            
            # Should propagate the exception
            with pytest.raises(Exception, match="Action Error"):
                translatron(event, {})

    def test_empty_languages_list(self):
        """Test behavior with empty languages list."""
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1],
            languages=[]  # No target languages
        )
        
        message = {'text': 'Hello', 'sender': '+15559876543'}
        translations, original_lang = translatron.detect_and_translate(message)
        
        assert original_lang == "en"
        assert len(translations) == 0

    def test_single_language_same_as_detected(self):
        """Test when only target language is same as detected language."""
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[self.mock_action1],
            languages=["en"]  # Only English
        )
        
        self.mock_translator.detected_lang = "en"
        
        message = {'text': 'Hello', 'sender': '+15559876543'}
        translations, original_lang = translatron.detect_and_translate(message)
        
        assert original_lang == "en"
        assert len(translations) == 0  # No translation needed

    def test_get_conversation_id_method(self):
        """Test the _get_conversation_id method."""
        event = {'From': '+15551234567'}
        result = self.translatron._get_conversation_id(event)
        assert result == '+15551234567'
        
        # Test with missing From field
        event = {}
        result = self.translatron._get_conversation_id(event)
        assert result == ''

    def test_parse_event_with_unicode_text(self):
        """Test parsing event with Unicode characters."""
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Hello 世界 🌍'
        }
        event = {
            'body': urlencode(body_data, encoding='utf-8'),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='unicode-test-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T19:00:00'
            
            result = self.translatron.parse_event(event)
            assert result['text'] == 'Hello 世界 🌍'

    def test_detect_and_translate_with_empty_text(self):
        """Test detect_and_translate with empty text."""
        message = {'text': '', 'sender': '+15559876543'}
        
        translations, original_lang = self.translatron.detect_and_translate(message)
        
        # Should still work with empty text
        assert isinstance(original_lang, str)
        assert isinstance(translations, list)

    def test_with_real_nontranslator(self):
        """Test integration with real NonTranslator."""
        real_translator = NonTranslator()
        null_action = NullAction()
        
        translatron = TranslatronText(
            translator=real_translator,
            actions=[null_action],
            languages=["en", "es", "fr"]
        )
        
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Real translator test'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime, \
             patch('translatron.actions.logger'):
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='real-translator-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T20:00:00'
            
            response = translatron(event, {})
            
            assert response['statusCode'] == 200
            assert response['body'] == '<Response></Response>'

    def test_multiple_actions_with_different_behaviors(self):
        """Test with multiple actions that have different behaviors."""
        action1 = MockAction()
        action2 = MockAction()
        
        # Create an action that modifies something (though it shouldn't modify the record)
        action3 = Mock()
        
        translatron = TranslatronText(
            translator=self.mock_translator,
            actions=[action1, action2, action3],
            languages=["es"]
        )
        
        body_data = {
            'From': '+15551234567',
            'To': '+15559876543',
            'Body': 'Multiple actions test'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='multi-action-id')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T21:00:00'
            
            response = translatron(event, {})
            
            # All actions should have been called
            assert len(action1.called_with) == 1
            assert len(action2.called_with) == 1
            action3.assert_called_once()
            
            # Response should still be correct
            assert response['statusCode'] == 200

    def test_malformed_base64_body(self):
        """Test handling of malformed base64 encoded body."""
        event = {
            'body': 'invalid-base64!@#',
            'isBase64Encoded': True
        }
        
        # Should raise an exception when trying to decode invalid base64
        with pytest.raises(Exception):
            self.translatron.parse_event(event)

    def test_conversation_id_extraction(self):
        """Test that conversation_id is properly extracted and matches sender."""
        body_data = {
            'From': '+15557654321',
            'To': '+15559876543',
            'Body': 'Conversation ID test'
        }
        event = {
            'body': urlencode(body_data),
            'isBase64Encoded': False
        }
        
        with patch('translatron.text.uuid.uuid4') as mock_uuid, \
             patch('translatron.text.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value='conv-id-test')
            mock_datetime.datetime.utcnow.return_value.isoformat.return_value = '2023-01-01T22:00:00'
            
            result = self.translatron.parse_event(event)
            
            assert result['conversation_id'] == result['sender']
            assert result['conversation_id'] == '+15557654321'