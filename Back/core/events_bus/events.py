import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from Back.utils.redis import to_serializable


class EventDataBase(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

class EventBase(BaseModel):
    event: str
    data: EventDataBase
    status: str = "OK"
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

    @field_validator("event", "status", mode='before')
    @classmethod
    def normalize_string_fields(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v


class ErrorCode(str, Enum):
    UNKNOWN_EVENT = "unknown_event"
    INVALID_DATA = "invalid_data"
    NOT_EVENT_TYPE = "not_event_type"
    HANDLER_ERROR = "handler_error"

class ErrorData(EventDataBase):
    code: ErrorCode
    details: str

class ErrorEvent(EventBase):
    event: Literal["ERROR"] = "ERROR"
    status: Literal["ERROR"] = "ERROR"
    data: ErrorData

    @staticmethod
    def create_error_event(
        code: ErrorCode,
        details: str,
    ):
        return ErrorEvent(
            data=ErrorData(
                code=code,
                details=details,
            ),
        )
