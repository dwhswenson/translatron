#!/usr/bin/env python
import base64
import json
import os
from urllib.parse import quote_plus

from twilio.request_validator import RequestValidator

from translatron.text import TranslatronText
from translatron.translator import NonTranslator


def create_test_event(url, param_dict, token):
    signature = RequestValidator(token).compute_signature(url, param_dict)
    form_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in param_dict.items())
    return {
        "body": base64.b64encode(form_data.encode()).decode(),
        "isBase64Encoded": True,
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
            "host": url.split("/")[2],
            "x-twilio-signature": signature
        },
        "httpMethod": "POST"
    }

if __name__ == "__main__":
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not token:
        raise ValueError("TWILIO_AUTH_TOKEN environment variable is not set.")

    texter = TranslatronText(
        translator=NonTranslator(),
        actions=[],
        languages=[],
    )

    url = "https://example.com/"
    param_dict = {
        "From": "+1234567890",
        "To": "+0987654321",
        "Body": "Hello world",
    }
    event = create_test_event(url, param_dict, token)

    # Validate the event using the texter instance
    params = texter.parse_event_params(event)
    if not texter.validate_twilio_event(params, event["headers"]):
        raise ValueError("Created test event failed validation!")

    print(json.dumps(event, indent=2))
