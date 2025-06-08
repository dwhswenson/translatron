import os
import json
from twilio.rest import Client as TwilioClient

from translatron.text import TranslatronText
from translatron.translator import AmazonTranslator
from translatron.actions import StoreToDynamoDB, SendTranslatedSMS

import logging
logging.getLogger('translatron').setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

class MyTranslatron(TranslatronText):
    pass


print("Creating StoreToDynamoDB action")
table_name = os.environ["DYNAMODB_TABLE"]
store_dynamodb_action = StoreToDynamoDB(table_name)

print("Creating SendTranslatedSMS action")
user_info = json.loads(os.getenv('USER_INFO'))
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_client = TwilioClient(account_sid, auth_token)
send_sms_action = SendTranslatedSMS(user_info, twilio_client)

print("Creating MyTranslatron instance")
target_languages = os.getenv("TARGET_LANGUAGES").split(",")
lambda_handler = MyTranslatron(
    translator=AmazonTranslator(),
    actions=[store_dynamodb_action, send_sms_action],
    languages=target_languages,
)
