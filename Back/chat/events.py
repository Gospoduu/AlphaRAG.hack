from ..events import EventDataBase, EventBase, ErrorEvent, ErrorData
from pydantic import Field
from datetime import datetime
from uuid import UUID
from .models import Role
from typing import Optional

# server events
class NewTokenData(EventDataBase):
    token: str
    chat_id: int
    id: int

class EndGenerationData(EventDataBase):
    chat_id: int
    details: str

class MessageResponseData(EventDataBase):
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
    last_id: str | None = None
    chat_id: int
    last_token_id: int | None = None

class GenerationRestoreEvent(EventBase):
    event: str = "generation_restore"
    status: str = "ok"
    data: GenerationRestoreData

class GeneratedTextEvent(EventBase):
    status: str = "ok"
    event: str = "generated_text"
    data: GeneratedTextData

class MessageResponseEvent(EventBase):
    event: str = "message_response"
    status: str = "ok"
    data: MessageResponseData


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

class ReconnectionErrorData(ErrorData):
    details: str
    chat_id: int
class ReconnectionErrorEvent(EventBase):
    event: str = "reconnection_error"
    status: str = "error"
    data: ReconnectionErrorData

server_events = [NewTokenEvent, EndGenerationEvent, GeneratedTextEvent ]
client_events = [NewMessageEvent, GenerationRestoreEvent]
server_events_dict = {e.model_fields["event"].default: e for e in server_events}
client_events_dict = {e.model_fields["event"].default: e for e in client_events}


