from ..events import EventDataBase, EventBase
from pydantic import Field
from datetime import datetime
from uuid import UUID
from models import Role


# server events
class NewTokenData(EventDataBase):
    token: str
    chat_id: int

class EndGenerationData(EventDataBase):
    chat_id: int
    details: str

class MessageResponseData(EventDataBase):
    id: int
    local_id: int
    chat_id: int
    user_uuid: UUID
    text: str
    answered_to: int
    user_role: str = Role.USER.value

class GeneratedTextData(EventDataBase):
    chat_id: int
    text: str

class GeneratedTextEvent(EventBase):
    status: str = "ok"
    event: str = "generated_text"

class MessageResponseEvent(EventBase):
    event = "message_response"
    status: str = "ok"
    data: MessageResponseData


class NewTokenEvent(EventBase):
    event = "new_token"
    status: str = "ok"
    data: NewTokenData

class EndGenerationEvent(EventBase):
    status: str = "ok"
    event = "end_generation"
    data: EndGenerationData

# client event
class NewMessageData(EventDataBase):
    user_uuid: UUID
    chat_id: int
    text: str = Field(min_length=1, max_length=1000)
    answered_to: int | None = None
    role: str = Role.USER.value


class NewMessageEvent(EventBase):
    event = "new_message"
    status: str = "ok"
    data: NewMessageData

server_events = [NewTokenEvent, EndGenerationEvent ]
client_events = [NewMessageEvent]
server_events_dict ={e.event: e for e in server_events}
client_events_dict ={e.event: e for e in client_events}
