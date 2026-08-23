# Back/modules/chat/events.py
from typing import Literal
from uuid import UUID

from pydantic import Field

from Back.constants import (
    EVENT_NEW_TOKEN,
    EVENT_NEW_MESSAGE,
    EVENT_END_GENERATION,
    EVENT_GENERATED_TEXT,
    EVENT_MESSAGE_RESPONSE,
    EVENT_GENERATION_RESTORE,
    STATUS_OK
)
from Back.modules.chat.models import Role
from Back.core.events_bus.events import EventDataBase, EventBase

# server events
class NewTokenData(EventDataBase):
    token: str
    chat_id: int
    id: int
    user_uuid: UUID

class EndGenerationData(EventDataBase):
    chat_id: int
    user_uuid: UUID
    details: str
    all_text: str

class NewMessageResponseData(EventDataBase):
    id: int
    local_id: int
    chat_id: int
    user_uuid: UUID
    text: str
    answered_to: int | None = None
    user_role: str = Role.USER.value

class GeneratedTextData(EventDataBase):
    chat_id: int
    text: str

class GenerationRestoreData(EventDataBase):
    user_uuid: UUID
    last_id: str | None = None
    chat_id: int

# client event
class NewMessageData(EventDataBase):
    user_uuid: UUID
    chat_id: int
    text: str = Field(min_length=1, max_length=1000)
    answered_to: int | None = None
    role: str = Role.USER.value

class GenerationRestoreEvent(EventBase):
    event: Literal[EVENT_GENERATION_RESTORE] = EVENT_GENERATION_RESTORE
    status: Literal[STATUS_OK] = STATUS_OK
    data: GenerationRestoreData

class GeneratedTextEvent(EventBase):
    event: Literal[EVENT_GENERATED_TEXT] = EVENT_GENERATED_TEXT
    status: Literal[STATUS_OK] = STATUS_OK
    data: GeneratedTextData

class NewMessageResponseEvent(EventBase):
    event: Literal[EVENT_MESSAGE_RESPONSE] = EVENT_MESSAGE_RESPONSE
    status: Literal[STATUS_OK] = STATUS_OK
    data: NewMessageResponseData


class NewTokenEvent(EventBase):
    event: Literal[EVENT_NEW_TOKEN] = EVENT_NEW_TOKEN
    status: Literal[STATUS_OK] = STATUS_OK
    data: NewTokenData

class EndGenerationEvent(EventBase):
    event: Literal[EVENT_END_GENERATION] = EVENT_END_GENERATION
    status: Literal[STATUS_OK] = STATUS_OK
    data: EndGenerationData


class NewMessageEvent(EventBase):
    event: Literal[EVENT_NEW_MESSAGE] = EVENT_NEW_MESSAGE
    status: Literal[STATUS_OK] = STATUS_OK
    data: NewMessageData
