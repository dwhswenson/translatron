# src/translatron/record.py

from typing import List, Dict
from pydantic import BaseModel


class TextRecord(BaseModel):
    """
    A class representing a record with an ID and content.
    """

    message_id: str
    conversation_id: str
    sender: str
    recipient: str
    original_lang: str
    original_text: str
    translations: List[Dict[str, str]]
    timestamp: str
