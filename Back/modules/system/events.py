from Back.core.events_bus.events import EventBase, EventDataBase
from pydantic import Field

class PongData(EventDataBase):
    pass

class PongEvent(EventBase):
    event: str = "pong"
    status: str
    data: PongData = Field(
        default_factory=PongData,
    )

class PingData(EventDataBase):
    pass

class PingEvent(EventBase):
    event: str = "ping"
    status: str = "ok"
    data: PingData = Field(default_factory=PingData)
