# Back/modules/chat/handlers

from  uuid import UUID
from dotenv import load_dotenv
from pathlib import Path
import logging
import asyncio
import os

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from Back.core.events_bus.handler_policy import with_policy
from Back.core.events_bus.events import ErrorEvent, ErrorCode
from Back.modules.chat.events import (
    NewMessageEvent,
    GenerationRestoreEvent,
    NewTokenEvent,
    NewTokenData,
    EndGenerationEvent,
    NewMessageResponseEvent,
    NewMessageResponseData,
    GeneratedTextEvent,
    GeneratedTextData,
    EndGenerationData
)
from Back.modules.user.models import Role
from Back.infra.redis.streams import add_new_emit
from Back.infra.kafka.publishers import publish_message
from . import crud
from .streams import add_new_chat_stream, read_chat_stream_since

from ...core.events_bus.event_manager import event_manager

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

LLM_USER_UUID = UUID(os.getenv("LLM_USER_UUID"))
logger.info("LLM_USER_UUID=%s", LLM_USER_UUID)



async def llm_answer_plug(prompt: str):
    ans = f"Тут мог быть ответ ЛЛМ на этот промпт: `{prompt}`\n"
    for s in range(1,len(ans), 2):
        await asyncio.sleep(0.1)
        yield ans[s - 1] + ans[s]


@with_policy()
async def message_handler(
        new_message: NewMessageEvent,
        redis: Redis,
        db: AsyncSession)-> None:
    try:
        updated_local_id = await crud.get_last_message_local_id(db=db, chat_id=new_message.data.chat_id) or 0
        updated_local_id+=1
        message_model = await crud.create_message(
            db=db,
            chat_id=new_message.data.chat_id,
            text=new_message.data.text,
            user_uuid=new_message.data.user_uuid,
            answered_to=new_message.data.answered_to,
            local_id=updated_local_id,
            user_role=new_message.data.role

        )
        message_response_event = NewMessageResponseEvent(
            data=NewMessageResponseData(
                id=message_model.id,
                chat_id=new_message.data.chat_id,
                text=new_message.data.text,
                answered_to=new_message.data.answered_to,
                user_uuid=new_message.data.user_uuid,
                local_id=updated_local_id,
            )
        )
        await add_new_emit(redis=redis, event=message_response_event, user_uuid=new_message.data.user_uuid)
        status = await crud.get_is_generate(db=db, chat_id=new_message.data.chat_id)
        if status:
            logger.info("LLM answer received, try later again!")
            return
        await crud.change_is_generate(db=db, chat_id=new_message.data.chat_id, new_is_generate=True)
        await db.commit()

        await publish_message(new_message)

    except Exception as e:
        try:
            await db.rollback()
            await add_new_emit(redis=redis, event=ErrorEvent.create_error_event(ErrorCode.HANDLER_ERROR, str(e)), user_uuid=new_message.data.user_uuid)
            logger.error("", exc_info=True)
        except Exception:
            logger.error("Failed to send error message", exc_info=True)
        raise

@with_policy()
async def llm_answer_handler(
        new_message: NewMessageEvent,
        db: AsyncSession,
        redis: Redis,
)->None:
    try:
        status = await crud.get_is_generate(db=db, chat_id=new_message.data.chat_id)
        if status:
            logger.info("LLM answer received, try later again!")
            return
        await crud.change_is_generate(db=db, chat_id=new_message.data.chat_id, new_is_generate=True)
        await db.commit()
        prompt = new_message.data.text
        token_id = 0

        ans = ""
        async for token in llm_answer_plug(prompt):
            token_event = NewTokenEvent(
                data=NewTokenData(
                    id=token_id,
                    token=token,
                    chat_id=new_message.data.chat_id,
                )
            )
            last_id = await add_new_chat_stream(redis=redis, event=token_event, chat_id=new_message.data.chat_id)
            token_event.meta["last_id"] = last_id
            await add_new_emit(redis=redis, event=token_event, user_uuid=new_message.data.user_uuid)
            print(f"Token {token}, id {token_id} was added")
            ans+=token
            token_id += 1
        end_generation_event = EndGenerationEvent(
            data=EndGenerationData(
                chat_id=new_message.data.chat_id,
                details="Generation ends successfully",
            )
        )

        await add_new_emit(redis=redis, event=end_generation_event, user_uuid=new_message.data.user_uuid)
        updated_local_id = await crud.get_last_message_local_id(db=db, chat_id=new_message.data.chat_id) or 0
        updated_local_id += 1
        await crud.create_message(
            db=db,
            chat_id=new_message.data.chat_id,
            text=ans,
            user_uuid=LLM_USER_UUID,
            answered_to=None,
            local_id=updated_local_id,
            user_role=Role.BOT,
        )
        await db.commit()
        logger.info(f"Generation chat {new_message.data.chat_id} ends successfully ")

    except Exception:
        logger.error(f"Generation chat {new_message.data.chat_id} failed", exc_info=True)
        try:
            await add_new_emit(redis=redis, event=ErrorEvent.create_error_event(ErrorCode.HANDLER_ERROR, "Failed generation"), user_uuid=new_message.data.user_uuid)
        except Exception:
            logger.error(f"Failed to send error message to redis, chat_id {new_message.data.chat_id}", exc_info=True)
        raise

    finally:
        try:
            try:
                await db.rollback()
            except Exception:
                pass
            await crud.change_is_generate(db=db, chat_id=new_message.data.chat_id, new_is_generate=False)
            await db.commit()
        except Exception:
            logger.error("Failed to change chat generation status", exc_info=True)

@with_policy(retry=True)
async def restore_handler(event: GenerationRestoreEvent, redis: Redis, db: AsyncSession)->None:
    try:
        chat_id = event.data.chat_id
        last_id = event.data.last_id or "0-0"
        cached = await read_chat_stream_since(chat_id, redis, last_id)
        parts = []
        if not cached:
            return
        last_seen_id = last_id
        last_seen_token_id = None
        for entry_id, entry_data in cached:
            event_name = entry_data.get("event")
            payload = entry_data.get("payload")
            if not event_name or not payload:
                continue
            if event_name != NewTokenEvent.model_fields["event"].default:
                logger.warning(f"Event {event_name} was ignored in restore handler")
                continue
            event_cls = event_manager.get(event_name)
            if event_cls is None:
                logger.warning("Unknown event in restore handler: %s", event_name)
                continue
            try:
                parsed_token = event_cls.from_json(payload)
            except Exception:
                logger.warning("Bad token payload in restore handler: entry_id=%s", entry_id, exc_info=True)
                continue
            token_text = parsed_token.data.token
            parts.append(token_text)
            last_seen_id = entry_id
            last_seen_token_id = parsed_token.data.id

        if not parts:
            return
        restore_event =  GeneratedTextEvent(
            data=GeneratedTextData(
                chat_id=chat_id,
                text="".join(parts),
            )
        )
        restore_event.meta["last_id"] = last_seen_id
        restore_event.meta["last_token_id"] = last_seen_token_id

        await add_new_emit(redis=redis, event=restore_event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error(f"Restore generation for chat: {event.data.chat_id} failed", exc_info=True)
        try:
            await add_new_emit(redis=redis, event=ErrorEvent.create_error_event(ErrorCode.HANDLER_ERROR, "Failed restщку generation"), user_uuid=event.data.user_uuid)
        except Exception:
            logger.error(f"Failed to send error message to redis, chat_id {event.data.chat_id}", exc_info=True)
        raise
