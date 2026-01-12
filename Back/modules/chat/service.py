from typing import AsyncGenerator, Callable
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from Back.infra.redis.streams import add_new_emit
from .crud import create_message, get_last_message_local_id
from Back.modules.chat.events import NewMessageEvent, MessageResponseEvent, MessageResponseData
from Back.core.events_bus.events import EventBase, ErrorEvent, ConnectionErrorData, InvalidDataError
from .models import Role

from logging import getLogger
logger = getLogger(__name__)

async def message_resp(
        user_uuid: UUID,
        message: NewMessageEvent,
        db: AsyncSession,
        redis: Redis
)-> EventBase:
    try:
        last_message_local_id = await get_last_message_local_id(
            db,
            message.data.chat_id
        ) or 0
        new_message =  await create_message(
            db=db,
            user_uuid=message.data.user_uuid,
            chat_id=message.data.chat_id,
            local_id=last_message_local_id + 1,
            text=message.data.text,
            user_role=Role.USER.value,
        )
        await db.commit()
        print(f"✅ Message saved: {new_message.id}, {new_message.text}")
        await add_new_emit(user_uuid, MessageResponseEvent(
            data=MessageResponseData(
                id=new_message.id,
                text=new_message.text,
                user_uuid=new_message.user_uuid,
                chat_id=new_message.chat_id,
                user_role=new_message.user_role,
                answered_to=new_message.answered_to,
                local_id=new_message.local_id,
            )
        ), redis)
    except ConnectionError:
        await db.rollback()
        await add_new_emit(user_uuid, ErrorEvent(
            data=ConnectionErrorData(details="Database connection lost.")
        ), redis)
    except AttributeError as e:
        await db.rollback()
        await add_new_emit(user_uuid, ErrorEvent(
            data=InvalidDataError(
                details=f"Invalid message data structure: {str(e)}. Got: {message.data.model_dump()}"
            )
        ), redis)
    except Exception as e:
        print(f"❌ Error in message_handler: {str(e)}")
        await db.rollback()
        await add_new_emit(user_uuid, ErrorEvent(data=InvalidDataError(details=str(e))), redis)



async def llm_answer_resp(
        new_message: NewMessageEvent,
        db: AsyncSession,
        redis: Redis,
        llm_answer_generator: Callable,
)->AsyncGenerator[EventBase, None]:
    pass


async def llm_answer_pipeline_handler(
        new_message: NewMessageEvent,
        db: AsyncSession,
        redis: Redis
):
    pass
