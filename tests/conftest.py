import pytest
from unittest.mock import Mock

from translatron.record import TextRecord
from twilio.rest import Client as TwilioClient


@pytest.fixture
def basic_text_record():
    return TextRecord(
        message_id="test-msg-123",
        conversation_id="conv-456",
        sender="+15559876543",
        recipient="+15551234567",  # Messaging number
        original_lang="en",
        original_text="Hello world",
        translations=[
            {"lang": "es", "text": "Hola mundo"},
            {"lang": "fr", "text": "Bonjour le monde"}
        ],
        timestamp="2023-01-01T12:00:00Z"
    )


@pytest.fixture
def user_info_data():
    return {
        "+15551234567": {
            "+15559876543": {"name": "Alice", "lang": "en"},
            "+15559876544": {"name": "Bob", "lang": "es"},
            "+15559876545": {"name": "Charlie", "lang": "fr"},
        },
        "+15551111111": {
            "+15552222222": {"name": "Dave", "lang": "en"},
            "+15553333333": {"name": "Eve", "lang": "es"},
        }
    }


@pytest.fixture
def mock_twilio_client():
    mock_client = Mock(spec=TwilioClient)
    mock_client.messages = Mock()
    mock_client.messages.create = Mock()
    return mock_client


@pytest.fixture
def sample_twilio_event():
    return {
        'body': 'From=%2B15551234567&To=%2B15559876543&Body=Hello%20world',
        'isBase64Encoded': False,
        'headers': {
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'example.com',
            'x-twilio-signature': 'test_signature'
        }
    }


@pytest.fixture
def sample_base64_twilio_event():
    import base64
    from urllib.parse import urlencode

    body_data = {
        'From': '+15551234567',
        'To': '+15559876543',
        'Body': 'Base64 encoded message'
    }
    body_str = urlencode(body_data)
    encoded_body = base64.b64encode(body_str.encode('utf-8')).decode('utf-8')

    return {
        'body': encoded_body,
        'isBase64Encoded': True,
        'headers': {
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'example.com',
            'x-twilio-signature': 'test_signature'
        }
    }
