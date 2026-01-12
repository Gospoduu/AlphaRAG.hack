from uuid import UUID

from pydantic import BaseModel, Field
from .models import Role

class CreateUserBase(BaseModel):
    role: Role = Role.USER
