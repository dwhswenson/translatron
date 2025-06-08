import os
import uuid
import json
import datetime
import base64
from urllib.parse import parse_qs

import boto3

from translator import AmazonTranslator, GoogleTranslator

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
TRANSLATOR_PROVIDER = os.getenv("TRANSLATOR_PROVIDER", "amazon").lower()
TARGET_LANGUAGES = os.getenv("TARGET_LANGUAGES").split(",")


def get_translator():
    provider_type = os.getenv("TRANSLATOR_PROVIDER", "amazon").lower()
    provider = {
        "amazon": AmazonTranslator,
        "google": GoogleTranslator
    }[provider_type]
    return provider()


translator = get_translator()

### Temporary setup
def forward_message(record):
    translations = record['translations']
    translations.append({'lang': record['original_lang'], 'text':
                        record['original_text']})

    translations_dict = {t['lang']: t['text'] for t in translations}

    users = json.loads(os.getenv('USER_INFO'))
    users = users[os.environ['TWILIO_NUMBER']]

    # TODO: check if sender not in users? maybe do something different?
    targets = set(users) - {record['sender']}
    msg_pairs = [(target, users[target]['lang']) for target in targets]

    # special case override for testing
    if record['sender'] == '+13121234567':
        msg_pairs = [(os.getenv('TEST_PHONE'), 'fa')]

    for send_to, lang in msg_pairs:
        logger.info(f"sender={record['sender']} {send_to=} {lang=}")
        msg = translations_dict[lang]
        logger.info("About to send: %s", msg)
        from twilio.rest import Client
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        twilio_number = os.environ['TWILIO_NUMBER']
        logger.info("Connecting to client")
        client = Client(account_sid, auth_token)
        logger.info("Sending message")
        message = client.messages.create(  # noqa F841
            body=msg,
            from_=twilio_number,
            to=send_to
        )

import logging  # noqa E402
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Decode body if base64‑encoded
    logger.info(f"{translator=}")
    logger.info(f"{translator.translate=}")
    body_str = event.get("body", "")
    if event.get("isBase64Encoded", False):
        body_str = base64.b64decode(body_str).decode("utf-8")

    # Parse Twilio form‑encoded payload
    params = parse_qs(body_str)
    sender = params.get("From", [""])[0]
    logger.info("Received SMS from %s", sender)
    text   = params.get("Body", [""])[0]
    logger.info("SMS text: %s", text)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    logger.info("Timestamp: %s", timestamp)

    message_id = str(uuid.uuid4())
    logger.info("Message ID: %s", message_id)
    conversation_id = sender
    logger.info("Conversation ID: %s", conversation_id)

    # Detect source language and translate
    original_lang = translator.detect_language(text)
    logger.info("Detected language: %s", original_lang)
    translations = []
    for target in TARGET_LANGUAGES:
        if target == original_lang:
            continue
        translated_text = translator.translate(text, target,
                                               detected_language=original_lang)
        logger.info("Translated to %s: %s", target, translated_text)
        translations.append({"lang": target, "text": translated_text})

    record = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": sender,
        "original_lang": original_lang,
        "original_text": text,
        "translations": translations,
        "timestamp": timestamp,
    }

    dynamodb.Table(TABLE_NAME).put_item(Item=record)

    # TEMP: Send SMS translation; replace with push notification
    forward_message(record)

    return {
        "statusCode": 200,
        "body": "<Response></Response>",
        "headers": {"Content-Type": "application/xml"}
    }
