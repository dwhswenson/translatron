# src/translatron/actions.py
import os
import boto3
from typing import Optional, Dict, List, Tuple
from twilio.rest import Client as TwilioClient

from .record import TextRecord

import logging

logger = logging.getLogger(__name__)


class ActionBase:
    def __call__(self, record: TextRecord) -> None:
        raise NotImplementedError("Subclasses should implement this method.")


class NullAction(ActionBase):
    def __call__(self, record: TextRecord) -> None:
        """
        A no-op action that does nothing with the record.
        Useful for testing or as a placeholder.
        """
        logger.debug(f"NullAction called with record: {record}")
        # No operation performed, just logging the call


class StoreToDynamoDB(ActionBase):
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table = boto3.resource("dynamodb").Table(table_name)

    def __call__(self, record: TextRecord) -> None:
        logger.info(f"Storing record in {self.table_name}: {record}")
        self.table.put_item(Item=record.model_dump())


class SendTranslatedSMS(ActionBase):
    def __init__(
        self,
        user_info: Dict[str, Dict[str, Dict[str, str]]],
        twilio_client: TwilioClient,
    ):
        """
        Parameters
        ==========
        user_info: dict[str, dict[str, dict[str, str]]]
            Nested dictionary containing information to route messages to
            users. Structure is:
                {
                    "$MESSAGING_NUMBER":
                    {
                        "$USER_NUMBER": {
                            "name": "$NAME"
                            "lang": "$LANG",
                        }
                    }
                }
            where $MESSAGING_NUMBER is the Twilio number, $USER_NUMBER is
            the user's phone number, and $NAME and $LANG are the user's name
            and preferred language.
        """
        self.user_info = user_info
        self.twilio_client = twilio_client

    def _action_on_unknown_sender(self, record: TextRecord) -> None:
        """
        Handle the case where the sender is not recognized.
        This could be logging, sending a notification, etc.
        """
        logger.warning(f"Unknown sender: {record.sender}. Record: {record}")

    def _testing_override_msg_pairs(
        self, record: TextRecord
    ) -> Optional[List[Tuple[str, str]]]:
        """Returns a hardcoded message pair for testing purposes.

        This should return None if the record isn't a test case.
        """
        if record.sender == "+13121234567":
            return [(os.getenv("TEST_PHONE"), "fa")]

    def __call__(self, record: TextRecord) -> None:
        logger.info(f"Sending SMS with translated record: {record}")

        if record.recipient not in self.user_info:
            logger.error(
                f"Unknown recipient messaging number: {record.recipient}"
            )
            return

        users = self.user_info[record.recipient]

        # reorganize translation into easy-to-use dict
        translations = list(record.translations)
        translations.append(
            {"lang": record.original_lang, "text": record.original_text}
        )
        translations_dict = {t["lang"]: t["text"] for t in translations}

        if record.sender not in users:
            self._action_on_unknown_sender(record)
            return

        targets = set(users) - {record.sender}
        msg_pairs = [(target, users[target]["lang"]) for target in targets]
        msg_pairs = self._testing_override_msg_pairs(record) or msg_pairs

        for send_to, lang in msg_pairs:
            logger.info(f"sender={record.sender} {send_to=} {lang=}")
            msg = translations_dict.get(lang, record.original_text)
            if lang not in translations_dict:
                logger.warning(
                    f"No translation available for language '{lang}', using "
                    "original text"
                )
            logger.info("About to send: %s", msg)
            self.twilio_client.messages.create(
                body=msg,
                from_=record.recipient,  # Twilio number
                to=send_to,
            )
