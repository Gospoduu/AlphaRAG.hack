from pydantic import BaseModel, Field
from datetime import datetime

class EventDataBase(BaseModel):
    timestamp: datetime = Field(
        default_factory=datetime.now,
    )
    pass

class EventBase(BaseModel):
    event: str
    data: EventDataBase
    status: str


class PongData(EventDataBase):
    pass

class PongEvent(EventBase):
    event: str = "pong"
    status: str = "ok"
    data: PongData = Field(
        default_factory=PongData,
    )


class PingData(EventDataBase):
    pass

class PingEvent(EventBase):
    event: str = "ping"
    status: str = "ok"
    data: PingData = Field(default_factory=PingData)

class ErrorData(EventDataBase):
    details: str

class NotEventTypeErrorData(ErrorData):
    pass

class UnknownEventTypeErrorData(ErrorData):
    pass

class InvalidDataError(ErrorData):
    pass

class ConnectionErrorData(ErrorData):
    pass

class ErrorEvent(EventBase):
    event: str = "error"
    status: str = "error"
    data: ErrorData
error_events = [
    ErrorEvent,
]

server_events = [
    ErrorEvent,
    PongEvent,
]
server_events_dict = {e.event:e for e in server_events}
client_events = [
    PingEvent,
]
client_events_dict = {e.event:e for e in client_events}