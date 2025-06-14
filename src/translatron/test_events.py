"""Test event creation utilities for Twilio webhook testing."""

import base64
from typing import Dict, Any
from urllib.parse import quote_plus, parse_qs

from twilio.request_validator import RequestValidator


def create_twilio_test_event(
    url: str,
    param_dict: Dict[str, str],
    auth_token: str,
    base64_encode: bool = True,
) -> Dict[str, Any]:
    """Create a test event for Twilio webhook testing.
    
    Args:
        url: The full URL that Twilio will request (e.g. "https://example.com/")
        param_dict: Dictionary of POST variables (e.g. {"From": "+1234567890", "Body": "Hello"})
        auth_token: Your Twilio auth token
        base64_encode: Whether to base64 encode the body (default: True)
        
    Returns:
        A dictionary representing a Twilio webhook event that can be used for testing
    """
    # Generate Twilio signature
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(url, param_dict)
    
    # Create form-encoded body
    form_data = "&".join(f"{k}={quote_plus(str(v))}" for k, v in param_dict.items())
    
    # Create event
    event = {
        "body": base64.b64encode(form_data.encode()).decode() if base64_encode else form_data,
        "isBase64Encoded": base64_encode,
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
            "host": url.split("/")[2],
            "x-twilio-signature": signature
        },
        "httpMethod": "POST"
    }
    
    return event


def validate_test_event(event: Dict[str, Any], auth_token: str) -> bool:
    """Validate that a test event has a valid Twilio signature.
    
    Args:
        event: The test event to validate
        auth_token: Your Twilio auth token
        
    Returns:
        True if the event has a valid signature, False otherwise
    """
    validator = RequestValidator(auth_token)
    
    # Extract URL and parameters
    host = event["headers"]["host"]
    url = f"https://{host}/"
    
    # Parse parameters from body
    body = event["body"]
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode()
    
    # Parse form data using parse_qs to handle URL encoding properly
    params = parse_qs(body, keep_blank_values=True)
    # Convert lists to single values to match Twilio's format
    params = {k: v[0] for k, v in params.items()}
    
    # Validate signature
    signature = event["headers"]["x-twilio-signature"]
    return validator.validate(url, params, signature) 