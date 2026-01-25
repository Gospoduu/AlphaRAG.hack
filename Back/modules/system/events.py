# Back/modules/system/events.py

from Back.core.events_bus.events import EventBase, EventDataBase
from uuid import UUID

class PongData(EventDataBase):
    user_uuid: UUID


class PongEvent(EventBase):
    event: str = "pong"
    status: str = "ok"
    data: PongData

class PingData(EventDataBase):
    user_uuid: UUID

class PingEvent(EventBase):
    event: str = "ping"
    status: str = "ok"
    data: PingData
