# Twilio CLI Tool

A command-line interface (CLI) built with Python and [click](https://click.palletsprojects.com/) to manage Twilio phone numbers. This tool supports two subcommands:

- **purchase-number**: Searches for and purchases a new Twilio phone number in the specified area codes (defaults to 312 and 773). This command does not set webhooks unless required by the Twilio API.
- **set-webhooks**: Updates the SMS and voice webhook URLs for an existing Twilio phone number.

## Features

- **Purchase a Phone Number**: Automatically search for an available local phone number in your preferred area codes and purchase the first available one.
- **Update Webhooks**: Easily update the webhook URLs for SMS and voice on an existing Twilio number.
- **Configurable via Environment Variables**: Set your Twilio credentials and other settings via environment variables.

## Prerequisites

- Python 3.6 or higher
- A Twilio account with API credentials (Account SID and Auth Token)
- Internet access

## Installation

1. **Clone or Copy the Script**

   Copy the `twilio_cli.py` file into your project directory.

2. **Install Dependencies**

   Use pip to install the required packages:
   ```bash
   pip install twilio click


Environment Variables

The CLI requires the following environment variables to be set:
	•	TWILIO_ACCOUNT_SID: Your Twilio Account SID.
	•	TWILIO_AUTH_TOKEN: Your Twilio Auth Token.

For example, in your shell:

```bash
export TWILIO_ACCOUNT_SID=your_account_sid_here
export TWILIO_AUTH_TOKEN=your_auth_token_here
```

## Usage

Run the CLI using Python:

```bash
python twilio_cli.py <command> [options]
```

### purchase-number

This command searches for and purchases a new phone number in the preferred
area codes. It does not set webhook URLs unless required by the Twilio API.

Options:
*	--area-code, -a: Preferred area code to search for. This option can be
  provided multiple times.

#### Examples

```bash
python twilio_cli.py purchase-number
```

Or with custom area codes:

```bash
python twilio_cli.py purchase-number --area-code 312 --area-code 773
```

### set-webhooks

This command updates the SMS and voice webhook URLs for an existing Twilio
phone number.

Options:
*	--phone-number, -p: The phone number to update (in E.164 format, e.g.,
  +1234567890). (Required)
*	--sms-webhook: The URL for handling incoming SMS messages. (Required)
*	--voice-webhook: The URL for handling incoming voice calls. (Required)

#### Examples

```bash
python twilio_cli.py set-webhooks --phone-number +1234567890 --sms-webhook https://example.com/sms --voice-webhook https://example.com/voice
```
