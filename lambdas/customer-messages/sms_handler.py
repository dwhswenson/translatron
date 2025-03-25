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
BUCKET = os.environ["SMS_JSON_BUCKET"]
TRANSLATOR_PROVIDER = os.getenv("TRANSLATOR_PROVIDER", "amazon").lower()
TARGET_LANGUAGES = os.getenv("TARGET_LANGUAGES", "es,fr,de").split(",")


def get_translator():
    provider_type = os.getenv("TRANSLATOR_PROVIDER", "amazon").lower()
    provider = {
        "amazon": AmazonTranslator,
        "google": GoogleTranslator
    }[provider_type]
    return provider()


translator = get_translator()

import logging
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
        "timestamp": timestamp
    }

    # Persist metadata to DynamoDB
    dynamodb.Table(TABLE_NAME).put_item(Item={
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender": sender,
        "timestamp": timestamp
    })

    # Persist full JSON to S3
    key = f"sms/{timestamp[:10]}/{message_id}.json"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(record).encode("utf-8"),
        ContentType="application/json"
    )

    return {
        "statusCode": 200,
        "body": "<Response></Response>",
        "headers": {"Content-Type": "application/xml"}
    }
