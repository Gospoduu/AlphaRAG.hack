from pydantic import BaseModel
from models import Role

class CreateUserBase(BaseModel):
    role: Role = Role.USER