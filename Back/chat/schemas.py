from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from models import MessageReaction

class CreateChatBase(BaseModel):
    user_uuid: UUID
    model_config = ConfigDict(from_attributes=True)

class CreateMessageBase(BaseModel):
    user_uuid: UUID
    chat_id: int
    text: str = Field(min_length=1, max_length=1000)
    answered_to: int | None = None

class ReactionBase(BaseModel):
    message_id: int
    reaction: MessageReaction

class PongBase(BaseModel):
    ping: str