#!/usr/bin/env python
import os
import sys
import json
import click
from twilio.rest import Client

from .test_events import create_twilio_test_event, validate_test_event

# Retrieve Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    click.echo("Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables must be set.")
    sys.exit(1)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Default preferred area codes
DEFAULT_PREFERRED_AREA_CODES = ["312", "773"]

@click.group()
def cli():
    """CLI for managing Twilio phone numbers and test events."""
    pass

@cli.command("purchase-number")
@click.option(
    "--area-code", "-a",
    multiple=True,
    default=DEFAULT_PREFERRED_AREA_CODES,
    help="Preferred area code to search for. Can be provided multiple times."
)
def purchase_number(area_code):
    """
    Search for and purchase a new Twilio phone number in the specified area codes.
    This command does not set webhook URLs unless required by Twilio.
    """
    area_codes = list(area_code)
    click.echo(f"Searching for available phone numbers in area codes: {', '.join(area_codes)}")
    purchased_number = None

    for ac in area_codes:
        click.echo(f"Searching in area code {ac}...")
        try:
            available_numbers = client.available_phone_numbers("US").local.list(area_code=ac, limit=1)
        except Exception as e:
            click.echo(f"Error searching in area code {ac}: {e}")
            continue

        if available_numbers:
            phone_number_to_purchase = available_numbers[0].phone_number
            click.echo(f"Found available phone number: {phone_number_to_purchase}")
            try:
                # Purchase the number without setting webhooks.
                purchased = client.incoming_phone_numbers.create(
                    phone_number=phone_number_to_purchase,
                    friendly_name="Restaurant Phone Number"
                )
                purchased_number = purchased.phone_number
                click.echo(f"Purchased new phone number: {purchased_number}")
                break
            except Exception as e:
                click.echo(f"Error purchasing phone number {phone_number_to_purchase}: {e}")

    if not purchased_number:
        click.echo("No available phone number found in the specified area codes.")
        sys.exit(1)

@cli.command("set-webhooks")
@click.option(
    "--phone-number", "-p", 
    required=True, 
    help="The phone number to update (in E.164 format, e.g. +1234567890)."
)
@click.option(
    "--sms-webhook", 
    required=True, 
    help="The SMS webhook URL to set."
)
@click.option(
    "--voice-webhook", 
    required=True, 
    help="The voice webhook URL to set."
)
def set_webhooks(phone_number, sms_webhook, voice_webhook):
    """
    Update the webhook URLs for an existing Twilio phone number.
    """
    try:
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
    except Exception as e:
        click.echo(f"Error fetching phone number {phone_number}: {e}")
        sys.exit(1)

    if not numbers:
        click.echo(f"Phone number {phone_number} not found in your account.")
        sys.exit(1)

    number_instance = numbers[0]
    try:
        number_instance.update(
            sms_url=sms_webhook,
            sms_method="POST",
            voice_url=voice_webhook,
            voice_method="POST"
        )
        click.echo(f"Updated phone number {phone_number} with new webhooks.")
    except Exception as e:
        click.echo(f"Failed to update phone number {phone_number}: {e}")
        sys.exit(1)

@cli.command("create-test-event")
@click.option(
    "--url", "-u",
    default="https://example.com/",
    help="The full URL that Twilio will request (default: https://example.com/)"
)
@click.option(
    "--from-number", "-f",
    default="+1234567890",
    help="The 'From' phone number (default: +1234567890)"
)
@click.option(
    "--to-number", "-t",
    default="+0987654321",
    help="The 'To' phone number (default: +0987654321)"
)
@click.option(
    "--message", "-m",
    default="Hello world",
    help="The message body to include in the test event (default: Hello world)"
)
@click.option(
    "--no-base64/--base64",
    default=False,
    help="Whether to base64 encode the body (default: --base64)"
)
def create_test_event(url: str, from_number: str, to_number: str, message: str, no_base64: bool):
    """Create a test event for Twilio webhook testing.
    
    This command creates a test event that can be used to test your Twilio webhook
    handler. The event includes a valid Twilio signature and can be used with AWS
    Lambda test events or other testing tools.
    
    The default values match those used in the test suite:
    - URL: https://example.com/
    - From: +1234567890
    - To: +0987654321
    - Message: Hello world
    """
    # Create test event
    param_dict = {
        "From": from_number,
        "To": to_number,
        "Body": message,
    }
    
    event = create_twilio_test_event(
        url=url,
        param_dict=param_dict,
        auth_token=TWILIO_AUTH_TOKEN,
        base64_encode=not no_base64,
    )
    
    # Validate the event
    if not validate_test_event(event, TWILIO_AUTH_TOKEN):
        click.echo("Error: Generated test event failed validation!", err=True)
        sys.exit(1)
    
    # Output the event to stdout
    click.echo(json.dumps(event, indent=2))

if __name__ == '__main__':
    cli()
