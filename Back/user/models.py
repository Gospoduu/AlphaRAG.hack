from sqlalchemy import String, DateTime
from ..db.db import Base
from sqlalchemy.orm import mapped_column, Mapped
from uuid import uuid4, UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import datetime
from enum import Enum

class Role(str, Enum):
    USER = "user"
    BOT = "bot"
    OPERATOR = "operator"

class User(Base):
    __tablename__ = 'users'
    uuid: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    role: Mapped[Role] = mapped_column(
        String,
        nullable=False,
        default=Role.USER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
