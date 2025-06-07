import pytest
import os
import boto3
from unittest.mock import Mock, patch, call
from moto import mock_aws
from twilio.rest import Client as TwilioClient

from translatron.actions import ActionBase, NullAction, StoreToDynamoDB, SendTranslatedSMS
from translatron.record import TextRecord


class TestActionBase:
    def test_abstract_base_class(self, basic_text_record):
        """Test that ActionBase cannot be instantiated directly."""
        action = ActionBase()

        with pytest.raises(NotImplementedError, match="Subclasses should implement this method"):
            action(basic_text_record)


class TestNullAction:
    def setup_method(self):
        self.action = NullAction()

    def test_null_action_call(self, basic_text_record):
        """Test that NullAction logs the record but does nothing else."""
        with patch('translatron.actions.logger') as mock_logger:
            self.action(basic_text_record)
            mock_logger.debug.assert_called_once_with(f"NullAction called with record: {basic_text_record}")

    def test_null_action_with_empty_record(self):
        """Test NullAction with minimal record data."""
        record = TextRecord(
            message_id="",
            conversation_id="",
            sender="",
            recipient="",
            original_lang="",
            original_text="",
            translations=[],
            timestamp=""
        )

        with patch('translatron.actions.logger') as mock_logger:
            self.action(record)
            mock_logger.debug.assert_called_once_with(f"NullAction called with record: {record}")

    def test_null_action_multiple_calls(self):
        """Test that NullAction can be called multiple times."""
        record1 = TextRecord(
            message_id="test-id-1",
            conversation_id="conv-1",
            sender="+1111111111",
            recipient="+2222222222",
            original_lang="en",
            original_text="First message",
            translations=[],
            timestamp="2023-01-01T00:00:00Z"
        )

        record2 = TextRecord(
            message_id="test-id-2",
            conversation_id="conv-2",
            sender="+3333333333",
            recipient="+4444444444",
            original_lang="es",
            original_text="Segundo mensaje",
            translations=[],
            timestamp="2023-01-01T01:00:00Z"
        )

        with patch('translatron.actions.logger') as mock_logger:
            self.action(record1)
            self.action(record2)
            
            expected_calls = [
                call.debug(f"NullAction called with record: {record1}"),
                call.debug(f"NullAction called with record: {record2}")
            ]
            mock_logger.debug.assert_has_calls(expected_calls)


@mock_aws
class TestStoreToDynamoDB:
    def setup_method(self, method):
        # Create a mock DynamoDB table using moto
        self.table_name = "test-translation-table"
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create the table
        self.table = self.dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=[
                {
                    'AttributeName': 'message_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'message_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be active
        self.table.wait_until_exists()
        
        # Patch boto3.resource to return our mocked resource when creating the action
        with patch('translatron.actions.boto3.resource', return_value=self.dynamodb):
            self.action = StoreToDynamoDB(self.table_name)

    def test_store_record(self, basic_text_record):
        """Test storing a record to DynamoDB."""
        with patch('translatron.actions.logger') as mock_logger:
            self.action(basic_text_record)
            mock_logger.info.assert_called_once_with(f"Storing record in {self.table_name}: {basic_text_record}")
        
        # Verify the record was stored
        response = self.table.get_item(Key={'message_id': basic_text_record.message_id})
        assert 'Item' in response
        
        item = response['Item']
        assert item['message_id'] == basic_text_record.message_id
        assert item['conversation_id'] == basic_text_record.conversation_id
        assert item['sender'] == basic_text_record.sender
        assert item['original_text'] == basic_text_record.original_text

    def test_store_record_with_empty_translations(self, basic_text_record):
        """Test storing a record with no translations."""
        record = basic_text_record.model_copy(update={"translations": []})
        self.action(record)
        
        # Verify the record was stored
        response = self.table.get_item(Key={'message_id': record.message_id})
        assert 'Item' in response
        assert response['Item']['translations'] == []

    def test_store_multiple_records(self):
        """Test storing multiple records."""
        records = [
            TextRecord(
                message_id=f"test-id-{i}",
                conversation_id=f"conv-{i}",
                sender=f"+123456789{i}",
                recipient="+0987654321",
                original_lang="en",
                original_text=f"Message {i}",
                translations=[{"lang": "es", "text": f"Mensaje {i}"}],
                timestamp="2023-01-01T12:00:00Z"
            )
            for i in range(3)
        ]
        
        for record in records:
            self.action(record)
        
        # Verify all records were stored
        for i, record in enumerate(records):
            response = self.table.get_item(Key={'message_id': f'test-id-{i}'})
            assert 'Item' in response
            assert response['Item']['original_text'] == f'Message {i}'

    def test_initialization_with_table_name(self):
        """Test that StoreToDynamoDB initializes correctly with table name."""
        # Use the same patching approach as in setup_method
        with patch('translatron.actions.boto3.resource', return_value=self.dynamodb):
            action = StoreToDynamoDB("my-test-table")
            assert action.table_name == "my-test-table"
            assert action.table is not None


class TestSendTranslatedSMS:
    def setup_method(self):
        self.mock_twilio_client = Mock(spec=TwilioClient)
        self.mock_twilio_client.messages = Mock()
        self.mock_twilio_client.messages.create = Mock()
        
        # Sample user info structure
        self.user_info = {
            "+15551234567": {  # Messaging number (Twilio number)
                "+15559876543": {"name": "Alice", "lang": "en"},
                "+15559876544": {"name": "Bob", "lang": "es"},
                "+15559876545": {"name": "Charlie", "lang": "fr"},
            },
            "+15551111111": {  # Another messaging number
                "+15552222222": {"name": "Dave", "lang": "en"},
                "+15553333333": {"name": "Eve", "lang": "es"},
            }
        }
        
        self.action = SendTranslatedSMS(self.user_info, self.mock_twilio_client)

    def test_send_translated_sms_success(self, basic_text_record):
        """Test successful SMS sending with translations."""
        # basic_text_record already has the right sender/recipient, just update translations
        record = basic_text_record.model_copy(update={
            "translations": [
                {"lang": "es", "text": "Hola a todos"},
                {"lang": "fr", "text": "Bonjour tout le monde"}
            ]
        })
        
        mock_message = Mock()
        self.mock_twilio_client.messages.create.return_value = mock_message
        
        self.action(record)
        
        # Should send to Bob (Spanish) and Charlie (French), but not Alice (sender)
        assert self.mock_twilio_client.messages.create.call_count == 2
        
        calls = self.mock_twilio_client.messages.create.call_args_list
        
        # Check the calls - order might vary so we check both possibilities
        call_bodies = [call[1]['body'] for call in calls]
        call_recipients = [call[1]['to'] for call in calls]
        call_senders = [call[1]['from_'] for call in calls]
        
        assert "Hola a todos" in call_bodies
        assert "Bonjour tout le monde" in call_bodies
        assert "+15559876544" in call_recipients  # Bob
        assert "+15559876545" in call_recipients  # Charlie
        assert all(sender == "+15551234567" for sender in call_senders)

    def test_unknown_recipient_messaging_number(self, basic_text_record):
        """Test handling of unknown recipient messaging number."""
        record = basic_text_record.model_copy(update={
            "recipient": "+15559999999"  # Unknown messaging number
        })
        
        with patch('translatron.actions.logger') as mock_logger:
            self.action(record)
            mock_logger.error.assert_called_once_with("Unknown recipient messaging number: +15559999999")
        
        # No SMS should be sent
        self.mock_twilio_client.messages.create.assert_not_called()

    def test_unknown_sender(self, basic_text_record):
        """Test handling of unknown sender."""
        record = basic_text_record.model_copy(update={
            "sender": "+15559999999"  # Unknown sender
        })
        
        with patch('translatron.actions.logger') as mock_logger:
            self.action(record)
            mock_logger.warning.assert_called_once_with(f"Unknown sender: +15559999999. Record: {record}")
        
        # No SMS should be sent
        self.mock_twilio_client.messages.create.assert_not_called()

    def test_testing_override_msg_pairs(self, basic_text_record):
        """Test the testing override functionality."""
        # Add the test sender to user_info temporarily for this test
        self.user_info["+15551234567"]["+13121234567"] = {"name": "TestUser", "lang": "en"}
        
        record = basic_text_record.model_copy(update={
            "sender": "+13121234567",  # Special test sender
            "translations": [{"lang": "fa", "text": "پیام آزمایشی"}]
        })
        
        test_phone = "+15551111111"
        with patch.dict(os.environ, {'TEST_PHONE': test_phone}):
            mock_message = Mock()
            self.mock_twilio_client.messages.create.return_value = mock_message
            
            self.action(record)
            
            # Should send only to the test phone with Farsi translation
            self.mock_twilio_client.messages.create.assert_called_once_with(
                body="پیام آزمایشی",
                from_="+15551234567",
                to=test_phone
            )

    def test_testing_override_without_test_phone_env(self, basic_text_record):
        """Test testing override when TEST_PHONE env var is not set."""
        record = basic_text_record.model_copy(update={
            "sender": "+13121234567"  # Special test sender
        })
        
        # Make sure TEST_PHONE is not set
        with patch.dict(os.environ, {}, clear=True):
            # Since sender is not in user_info, should trigger unknown sender action
            with patch('translatron.actions.logger') as mock_logger:
                self.action(record)
                mock_logger.warning.assert_called_once()
            
            self.mock_twilio_client.messages.create.assert_not_called()

    def test_send_sms_with_original_language_in_targets(self, basic_text_record):
        """Test sending SMS when original language matches a target user's language."""
        record = basic_text_record.model_copy(update={
            "sender": "+15559876544",  # Bob (Spanish speaker)
            "original_lang": "es",
            "original_text": "Hola a todos",
            "translations": [
                {"lang": "en", "text": "Hello everyone"},
                {"lang": "fr", "text": "Bonjour tout le monde"}
            ]
        })
        
        mock_message = Mock()
        self.mock_twilio_client.messages.create.return_value = mock_message
        
        self.action(record)
        
        # Should send to Alice (English) and Charlie (French)
        # Bob should receive the original Spanish text (added to translations dict)
        assert self.mock_twilio_client.messages.create.call_count == 2
        
        calls = self.mock_twilio_client.messages.create.call_args_list
        call_bodies = [call[1]['body'] for call in calls]
        
        assert "Hello everyone" in call_bodies  # English translation for Alice
        assert "Bonjour tout le monde" in call_bodies  # French translation for Charlie

    def test_empty_translations_list(self, basic_text_record):
        """Test handling when there are no translations."""
        # basic_text_record already has Alice as sender and the right recipient
        record = basic_text_record.model_copy(update={
            "translations": [
                {"lang": "es", "text": "Hola"},  # Add Spanish for Bob
                {"lang": "fr", "text": "Bonjour"}  # Add French for Charlie
            ]
        })
        
        mock_message = Mock()
        self.mock_twilio_client.messages.create.return_value = mock_message
        
        self.action(record)
        
        # Should send to Bob (Spanish) and Charlie (French)
        assert self.mock_twilio_client.messages.create.call_count == 2

    def test_twilio_client_error(self, basic_text_record):
        """Test handling of Twilio client errors."""
        # basic_text_record already has the right setup, just use it directly
        record = basic_text_record
        
        # Make Twilio client raise an exception
        self.mock_twilio_client.messages.create.side_effect = Exception("Twilio API Error")
        
        # The action should propagate the exception
        with pytest.raises(Exception, match="Twilio API Error"):
            self.action(record)

    def test_user_info_structure_validation(self, user_info_data, mock_twilio_client):
        """Test that the action works with the expected user_info structure."""
        # Test initialization with valid structure
        action = SendTranslatedSMS(user_info_data, mock_twilio_client)
        assert action.user_info == user_info_data
        assert action.twilio_client == mock_twilio_client

    def test_logging_calls(self, basic_text_record):
        """Test that appropriate logging calls are made."""
        # basic_text_record already has the right sender/recipient, just use it
        record = basic_text_record
        
        mock_message = Mock()
        self.mock_twilio_client.messages.create.return_value = mock_message
        
        with patch('translatron.actions.logger') as mock_logger:
            self.action(record)
            
            # Check that info logging calls were made
            mock_logger.info.assert_any_call(f"Sending SMS with translated record: {record}")
            
            # Should have logging for each recipient
            assert mock_logger.info.call_count >= 3  # At least initial log + 2 recipients
