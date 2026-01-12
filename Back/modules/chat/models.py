from Back.infra.db.db import Base
from uuid import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import String,UniqueConstraint, ForeignKey, Integer, DateTime, Boolean
from datetime import datetime
from enum import Enum
from Back.modules.user.models import Role


class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    nullable=False)
    title: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=""
    )
    user_uuid: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.uuid",
                    ondelete="CASCADE"
                   ),
         nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
    is_generate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )




class MessageReaction(int, Enum):
    LIKE = 1
    NO_REACTION = 0
    DISLIKE = -1

class Message(Base):
    __tablename__ = 'messages'
    id :Mapped[int]=mapped_column(Integer,
                                  primary_key=True,
                                  autoincrement=True,
                                  nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    local_id: Mapped[int] = mapped_column(Integer,nullable=False)
    user_uuid :Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),

                                          ForeignKey("users.uuid",
                                                                 ondelete="CASCADE"
                                                                 ),
                                          nullable=False)
    user_role :Mapped[Role]=mapped_column(String,
                                          nullable=False,)
    text: Mapped[str] = mapped_column(String,
                                      nullable=False,
                                      default="")
    reaction: Mapped[MessageReaction]=mapped_column(Integer,
                                                    default=MessageReaction.NO_REACTION.value,
                                                    nullable=False
                                                    )
    answered_to: Mapped[int]=mapped_column(
        Integer,
        ForeignKey("messages.id",
                              ondelete="RESTRICT"
                   ),
        nullable=True,
        )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("chat_id", "local_id", "user_uuid", name="uq_message_local_per_chat"),
    )

class ChatMember(Base):
    __tablename__ = 'chat_members'
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_uuid: Mapped[UUID]=mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("chat_id", "user_uuid", name="uq_chat_member"),
    )
class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False
    )

    operator_uuid: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="RESTRICT"),
        nullable=False,
    )
    user_uuid: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    answered_to: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.id",ondelete="RESTRICT"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    answer_text: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
    )
    was_answered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=None,
        nullable=True)
