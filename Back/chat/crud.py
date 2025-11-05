import uuid

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.util import await_only

from models import *
from uuid import UUID
from typing import Optional, List, AsyncGenerator

# =======Chats=======
# select
async def get_user_chats(
        db: AsyncSession,
        user_uuid: UUID)->List[Chat]:
    result = await db.execute(
        select(Chat)
        .where(Chat.user_uuid == user_uuid)
        .order_by(Chat.created_at.asc())
    )
    chats = result.scalars().all()
    return list(chats)

async def get_is_generate(
        db: AsyncSession,
        chat_id: int)->Optional[bool]:
    result = await db.execute(
        select(Chat.is_generate)
        .where(Chat.id == chat_id)
    )
    is_generate = result.scalars().first()
    return is_generate

# create
async def _create_chat_member(db: AsyncSession,
                              user_uuid: UUID,
                              chat_id: int) -> ChatMember:
    chat_member = ChatMember(chat_id=chat_id, user_uuid=user_uuid)
    db.add(chat_member)
    await db.flush()
    return chat_member

async def create_chat(db: AsyncSession,
                      user_uuid: UUID)-> Chat:
    chat = Chat(user_uuid=user_uuid)
    db.add(chat)
    await db.flush()
    chat_id = chat.id
    await _create_chat_member(db=db, user_uuid=user_uuid, chat_id=chat_id)
    await db.flush()
    return chat
# patch
async def change_is_generate(
        db: AsyncSession,
        chat_id: int,
        new_is_generate: bool)-> Optional[Chat]:
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise ValueError(f"Chat {chat_id} not found")
    setattr(chat, 'is_generate', new_is_generate)
    await db.flush()
    return chat

async def change_title(
        db: AsyncSession,
        chat_id: int,
        new_title: bool)-> Optional[Chat]:
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise ValueError(f"Chat {chat_id} not found")
    setattr(chat, 'title', new_title)
    await db.flush()
    return chat
# delete
async def delete_chat(db: AsyncSession,chat_id: int)-> None:
    chat = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id)
    )
    member = await db.execute(
        select(ChatMember)
        .where(ChatMember.chat_id == chat_id)
        .limit(1)
    )
    await db.delete(chat)
    await db.delete(member)
    await db.flush()
# =======Messages=======
# select
async def get_chat_batch(
        db: AsyncSession,
        chat_id: int,
        start_message_idx: int,
        batch_size: int) -> List[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.local_id.desc())
        .limit(batch_size)
        .offset(start_message_idx)
    )
    batch = result.scalars().all()
    return list(batch)
# create
async def create_message(
        db: AsyncSession,
        chat_id: int,
        user_uuid: UUID,
        local_id: int,
        user_role,
        text: str,
        answered_at: Optional[int] = None
)-> Message:
    new_message = Message(chat_id=chat_id, user_uuid=user_uuid, local_id=local_id, text=text,user_role=user_role or None, answered_at=answered_at)
    db.add(new_message)
    await db.flush()
    return new_message
# patch
async def update_react(db: AsyncSession,
                          message_id: UUID,
                          react: int) -> Optional[Message]:
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()
    if not message:
        raise ValueError(f"Message {message_id} not found")
    setattr(message, 'react', react)
    await db.flush()
    return message

# =======Tickets=======
# select

async def get_all_operator_tickets(
        db: AsyncSession,
        operator_uuid: UUID,
        was_answered: Optional[bool] = None,
)-> List[Ticket]:
    if was_answered == None:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.operator_uuid == operator_uuid )
        )
    else:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.operator_uuid == operator_uuid and Ticket.was_answered == was_answered)
        )
    tickets = result.scalars().all()
    return list(tickets)

# create
async def create_ticket(
        db: AsyncSession,
        user_uuid: UUID,
        operator_uuid: UUID,
        answered_to,
        question_text: str,
        answer_text: str,

)-> Ticket:
    new_ticket = Ticket(
        user_uuid=user_uuid,
        operator_uuid=operator_uuid,
        answered_to=answered_to,
        question_text=question_text,
        answer_text=answer_text,
    )
    db.add(new_ticket)
    await db.flush()
    return new_ticket
# patch
async def update_ticket(
        db: AsyncSession,
        ticket_id: int,
        answered_text: str,
) -> Optional[Ticket]:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise ValueError(f"Ticket {ticket_id} not found")
    if ticket.was_answered:
        raise ValueError(f"Ticket {ticket_id} already answered")
    setattr(ticket, 'answered_text', answered_text)
    setattr(ticket, 'was_answered', True)
    setattr(ticket, 'answered_at', datetime.now())
    await db.flush()
    return ticket


