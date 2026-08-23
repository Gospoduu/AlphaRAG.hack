import logging
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import os

from faststream import Depends
from faststream.kafka import KafkaMessage
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from Back.constants import EVENT_END_GENERATION, EVENT_NEW_TOKEN
from Back.modules.chat.events import (
    EndGenerationEvent,
    EndGenerationData,
    NewMessageEvent,
    NewTokenEvent,
    NewTokenData,
)
from Back.infra.db.db import get_db
from Back.infra.redis.cache_manager import get_redis

from Back.infra.kafka.broker import broker
from Back.infra.kafka.handlers.llm_handlers import new_token_handler, end_generation_handler

logger = logging.getLogger(__name__)

LLM_REQUEST_TOPIC = os.getenv("LLM_REQUEST_TOPIC")
LLM_RESPONSE_TOPIC = os.getenv("LLM_RESPONSE_TOPIC")

if not LLM_REQUEST_TOPIC:
    raise RuntimeError("LLM_REQUEST_TOPIC is not configured")

if not LLM_RESPONSE_TOPIC:
    raise RuntimeError("LLM_RESPONSE_TOPIC is not configured")

@broker.subscriber(
    LLM_RESPONSE_TOPIC,
    group_id="chat-service",
    max_workers=2,
)
async def handle_llm_response(
    msg: KafkaMessage,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    event_name: str = msg.headers.get("event_name")

    if not event_name:
        raise ValueError("Missing 'event_name' Kafka header")

    if event_name == EVENT_NEW_TOKEN:
        event = NewTokenEvent.model_validate_json(msg.body)
        await new_token_handler(event, redis=redis)

    elif event_name == EVENT_END_GENERATION:
        event = EndGenerationEvent.model_validate_json(msg.body)
        await end_generation_handler(event, db=db, redis=redis)

    else:
        raise ValueError(f"Unknown LLM response event: {event_name}")


@broker.subscriber(
    LLM_REQUEST_TOPIC,
    group_id="chat-service",
    max_workers=2,
)
async def mock_llm_service(
    msg: KafkaMessage,
) -> None:
    event = NewMessageEvent.from_json(msg.body)
    res = f"Это мог быть ответ от ллм на {event.data.text} но увы"
    for idx, i in enumerate(res):
        await asyncio.sleep(0.1)
        token_event = NewTokenEvent(
            data=NewTokenData(
                token=i,
                chat_id=event.data.chat_id,
                user_uuid=event.data.user_uuid,
                id=idx
            )
        )
        await broker.publish(
            token_event.to_json(),
            topic=LLM_RESPONSE_TOPIC,
            headers={"event_name": EVENT_NEW_TOKEN},
        )

    end_event = EndGenerationEvent(
        data=EndGenerationData(
            chat_id=event.data.chat_id,
            user_uuid=event.data.user_uuid,
            details="Mock generation completed",
            all_text=res,
        )
    )

    await broker.publish(
        end_event.to_json(),
        topic=LLM_RESPONSE_TOPIC,
        headers={"event_name": EVENT_END_GENERATION},
    )



