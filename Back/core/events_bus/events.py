import json
from enum import Enum

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from Back.utils.redis import to_serializable


class EventDataBase(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

class EventBase(BaseModel):
    event: str
    data: EventDataBase
    status: str = "ok"
    meta: dict = Field(default_factory=dict)
    def get_event_data(self) -> str:
        return self.event

    @classmethod
    def from_json(cls, payload: str):
        return cls.model_validate_json(payload)

    @classmethod
    def from_dict(cls, dct: dict):
        return cls.model_validate(dct)

    def to_json(self):
        # Преобразуем объект обратно в JSON
        return json.dumps(self.model_dump(), default=to_serializable)

class ErrorCode(str, Enum):
    UNKNOWN_EVENT = "unknown_event"
    INVALID_DATA = "invalid_data"
    NOT_EVENT_TYPE = "not_event_type"
    HANDLER_ERROR = "handler_error"

class ErrorData(EventDataBase):
    code: ErrorCode
    details: str

class ErrorEvent(EventBase):
    event: str = "error"
    status: str = "error"
    data: ErrorData
    @staticmethod
    def create_error_event(code: ErrorCode, details: str):
        return ErrorEvent(
            data=ErrorData(
                code=code,
                details=details,
            ),
        )


