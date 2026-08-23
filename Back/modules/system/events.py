# Back/modules/system/events.py

from uuid import UUID
from typing import Literal

from Back.constants import EVENT_PING, EVENT_PONG, STATUS_OK
from Back.core.events_bus.events import EventBase, EventDataBase


class PongData(EventDataBase):
    user_uuid: UUID


class PongEvent(EventBase):
    event: Literal[EVENT_PONG] = EVENT_PONG
    status: Literal[STATUS_OK] = STATUS_OK
    data: PongData

class PingData(EventDataBase):
    user_uuid: UUID

class PingEvent(EventBase):
    event: Literal[EVENT_PING] = EVENT_PING
    status: Literal[STATUS_OK] = STATUS_OK
    data: PingData
