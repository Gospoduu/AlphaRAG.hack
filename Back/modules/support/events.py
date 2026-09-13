from uuid import UUID
from typing import Literal

from pydantic import Field

from Back.core.events_bus.events import EventBase, EventDataBase

from Back.constants import (
    STATUS_OK,
    SUPPORT_REQUEST,
    SUPPORT_RESPONSE,
    SUPPORT_MESSAGE,
    USER_FEEDBACK_REQUEST,
    END_SUPPORT_DIALOG_REQUEST,
    USER_FEEDBACK_RESPONSE,
    UPDATE_DIALOG_STATUS
)

class SupportRequestData(EventDataBase):
    user_uuid: UUID
    chat_id: int | None = None
    text: str = Field(min_length=1, max_length=1000)

class SupportResponseData(EventDataBase):
    user_uuid: UUID
    chat_id: int | None = None
    support_dialog_id: UUID

class SupportMessageData(EventDataBase):
    user_uuid: UUID
    support_dialog_id: UUID
    text: str = Field(min_length=1, max_length=1000)

class EndSupportDialogRequestData(EventDataBase):
    user_uuid: UUID
    support_dialog_id: UUID

class UserFeedbackRequestData(EventDataBase):
    user_uuid: UUID
    support_dialog_id: UUID

class UserFeedbackResponseData(EventDataBase):
    user_uuid: UUID
    support_dialog_id: UUID
    feedback: int
    feedback_text: str | None = None

class UpdateDialogStatusData(EventDataBase):
    user_uuid: UUID
    support_dialog_id: UUID
    new_status: str




class SupportRequestEvent(EventBase):
    event: Literal[SUPPORT_REQUEST] = SUPPORT_REQUEST
    status: Literal[STATUS_OK] = STATUS_OK
    data: SupportRequestData

class SupportResponseEvent(EventBase):
    event: Literal[SUPPORT_RESPONSE] = SUPPORT_RESPONSE
    status: Literal[STATUS_OK] = STATUS_OK
    data: SupportResponseData

class SupportMessageEvent(EventBase):
    event: Literal[SUPPORT_MESSAGE] = SUPPORT_MESSAGE
    status: Literal[STATUS_OK] = STATUS_OK
    data: SupportMessageData

class EndSupportDialogEvent(EventBase):
    event: Literal[END_SUPPORT_DIALOG_REQUEST] = END_SUPPORT_DIALOG_REQUEST
    status: Literal[STATUS_OK] = STATUS_OK
    data: EndSupportDialogRequestData

class UserFeedbackRequestEvent(EventBase):
    event: Literal[USER_FEEDBACK_REQUEST] = USER_FEEDBACK_REQUEST
    status: Literal[STATUS_OK] = STATUS_OK
    data: UserFeedbackRequestData

class UserFeedbackResponseEvent(EventBase):
    event: Literal[USER_FEEDBACK_RESPONSE] = USER_FEEDBACK_RESPONSE
    status: Literal[STATUS_OK] = STATUS_OK
    data: UserFeedbackResponseData

class UpdateDialogStatusEvent(EventBase):
    event: Literal[UPDATE_DIALOG_STATUS] = UPDATE_DIALOG_STATUS
    status: Literal[STATUS_OK] = STATUS_OK
    data: UpdateDialogStatusData

supports_request_events_map = {
    SUPPORT_REQUEST: SupportRequestEvent,
    SUPPORT_MESSAGE: SupportMessageEvent,
    END_SUPPORT_DIALOG_REQUEST: EndSupportDialogEvent,
    USER_FEEDBACK_RESPONSE: UserFeedbackResponseEvent,
}