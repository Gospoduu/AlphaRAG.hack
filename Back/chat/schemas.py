from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class CreateChatBase(BaseModel):
    user_uid: UUID
    hat_model = ConfigDict(from_attributes=True)



