import os
import json
from typing import Optional, List, Tuple
from twilio.rest import Client as TwilioClient

from translatron.translator import AmazonTranslator
from translatron.text import TranslatronText
from translatron.actions import StoreToDynamoDB, SendTranslatedSMS
from translatron.record import TextRecord


import logging
logging.getLogger('translatron').setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

class MySendTranslatedSMS(SendTranslatedSMS):
    def _testing_override_msg_pairs(
        self, record: TextRecord
    ) -> Optional[List[Tuple[str, str]]]:
        if record.sender == "+13121234567":
            return [(os.getenv("TEST_PHONE"), "fa")]


table_name = os.environ["DYNAMODB_TABLE"]
store_dynamodb_action = StoreToDynamoDB(table_name)

user_info = json.loads(os.getenv('USER_INFO'))
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = TwilioClient(account_sid, auth_token)
send_sms_action = MySendTranslatedSMS(user_info, twilio_client)

target_languages = os.getenv("TARGET_LANGUAGES").split(",")
lambda_handler = TranslatronText(
    translator=AmazonTranslator(),
    actions=[store_dynamodb_action, send_sms_action],
    languages=target_languages,
)
