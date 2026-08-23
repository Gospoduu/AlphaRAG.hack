import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from Back.core.events_bus.events import ErrorEvent, ErrorCode
from Back.infra.redis.streams import add_new_emit
from Back.modules.chat import crud
from Back.modules.chat.streams import add_new_chat_stream
from Back.modules.chat.events import NewTokenEvent, EndGenerationEvent
from Back.modules.user.models import Role

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

LLM_USER_UUID = UUID(os.getenv("LLM_USER_UUID"))

async def new_token_handler(
    event: NewTokenEvent,
    redis: Redis,
) -> None:
    try:
        last_id = await add_new_chat_stream(redis=redis, event=event, chat_id=event.data.chat_id)
        event.meta["last_id"] = last_id
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error(..., exc_info=True)
        raise


async def end_generation_handler(
    event: EndGenerationEvent,
    db: AsyncSession,
    redis: Redis,
):
    try:
        updated_local_id = await crud.get_last_message_local_id(db=db, chat_id=event.data.chat_id) or 0
        updated_local_id += 1
        await crud.create_message(
            db=db,
            chat_id=event.data.chat_id,
            text=event.data.all_text,
            user_uuid=LLM_USER_UUID,
            answered_to=None,
            local_id=updated_local_id,
            user_role=Role.BOT,
        )
        await db.commit()
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
        logger.info(f"Generation chat {event.data.chat_id} ends successfully ")
    except Exception:
        logger.error(f"Generation chat {event.data.chat_id} failed", exc_info=True)
        try:
            await add_new_emit(
                redis=redis,
                event=ErrorEvent.create_error_event(
                    ErrorCode.HANDLER_ERROR,
                    "Failed generation"
                ),
                user_uuid=event.data.user_uuid
            )
        except Exception:
            logger.error(f"Failed to send error message to redis, chat_id {event.data.chat_id}", exc_info=True)
        raise

    finally:
        try:
            try:
                await db.rollback()
            except Exception:
                pass
            await crud.change_is_generate(db=db, chat_id=event.data.chat_id, new_is_generate=False)
            await db.commit()
        except Exception:
            logger.error("Failed to change chat generation status", exc_info=True)


