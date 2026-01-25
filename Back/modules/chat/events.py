from Back.core.events_bus.events import EventDataBase, EventBase, ErrorData
from pydantic import Field
from uuid import UUID
from Back.modules.chat.models import Role
from typing import Optional

# server events
class NewTokenData(EventDataBase):
    token: str
    chat_id: int
    id: int

class EndGenerationData(EventDataBase):
    chat_id: int
    details: str

class NewMessageResponseData(EventDataBase):
    id: int
    local_id: int
    chat_id: int
    user_uuid: UUID
    text: str
    answered_to: Optional[int]
    user_role: str = Role.USER.value

class GeneratedTextData(EventDataBase):
    chat_id: int
    text: str

class GenerationRestoreData(EventDataBase):
    user_uuid: UUID
    last_id: str | None = None
    chat_id: int

class GenerationRestoreEvent(EventBase):
    event: str = "generation_restore"
    status: str = "ok"
    data: GenerationRestoreData

class GeneratedTextEvent(EventBase):
    status: str = "ok"
    event: str = "generated_text"
    data: GeneratedTextData

class NewMessageResponseEvent(EventBase):
    event: str = "message_response"
    status: str = "ok"
    data: NewMessageResponseData


class NewTokenEvent(EventBase):
    event: str = "new_token"
    status: str = "ok"
    data: NewTokenData

class EndGenerationEvent(EventBase):
    status: str = "ok"
    event: str = "end_generation"
    data: EndGenerationData

# client event
class NewMessageData(EventDataBase):
    user_uuid: UUID
    chat_id: int
    text: str = Field(min_length=1, max_length=1000)
    answered_to: int | None = None
    role: str = Role.USER.value


class NewMessageEvent(EventBase):
    event: str = "new_message"
    status: str = "ok"
    data: NewMessageData
