import logging
import os

from faststream import Depends
from faststream.kafka import KafkaMessage
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from Back.constants import EVENT_END_GENERATION, EVENT_NEW_TOKEN
from Back.modules.chat.events import (
    EndGenerationEvent,
    NewTokenEvent,
)

from Back.infra.kafka.handlers.support_handlers import (
    support_response_handler,
    support_message_handler,
    support_status_changed_handler,
    support_feedback_request_handler,
)
from Back.modules.support.events import (
    SupportResponseEvent,
    SupportMessageEvent,
    UpdateDialogStatusEvent,
    UserFeedbackRequestEvent,
)
from Back.constants import (
    SUPPORT_RESPONSE,
    SUPPORT_MESSAGE,
    UPDATE_DIALOG_STATUS,
    USER_FEEDBACK_REQUEST,
)

from Back.infra.db.db import get_db
from Back.infra.redis.cache_manager import get_redis

from Back.infra.kafka.broker import broker
from Back.infra.kafka.handlers.llm_handlers import new_token_handler, end_generation_handler

logger = logging.getLogger(__name__)

LLM_REQUEST_TOPIC = os.getenv("LLM_REQUEST_TOPIC")
LLM_RESPONSE_TOPIC = os.getenv("LLM_RESPONSE_TOPIC")
SUPPORT_RESPONSE_TOPIC = os.getenv("SUPPORT_RESPONSE_TOPIC")

if not LLM_REQUEST_TOPIC:
    raise RuntimeError("LLM_REQUEST_TOPIC is not configured")

if not LLM_RESPONSE_TOPIC:
    raise RuntimeError("LLM_RESPONSE_TOPIC is not configured")

if not SUPPORT_RESPONSE_TOPIC:
    raise RuntimeError("SUPPORT_RESPONSE_TOPIC is not configured")


@broker.subscriber(
    LLM_RESPONSE_TOPIC,
    group_id="chat-service",
    max_workers=5,
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
    SUPPORT_RESPONSE_TOPIC,
    group_id="chat-service",
    max_workers=5,
)
async def handle_support_response(
    msg: KafkaMessage,
    redis: Redis = Depends(get_redis),
) -> None:
    event_name: str = msg.headers.get("event_name")

    if not event_name:
        raise ValueError("Missing 'event_name' Kafka header")

    if event_name == SUPPORT_RESPONSE:
        event = SupportResponseEvent.model_validate_json(msg.body)
        await support_response_handler(event, redis=redis)

    elif event_name == SUPPORT_MESSAGE:
        event = SupportMessageEvent.model_validate_json(msg.body)
        await support_message_handler(event, redis=redis)

    elif event_name == UPDATE_DIALOG_STATUS:
        event = UpdateDialogStatusEvent.model_validate_json(msg.body)
        await support_status_changed_handler(event, redis=redis)

    elif event_name == USER_FEEDBACK_REQUEST:
        event = UserFeedbackRequestEvent.model_validate_json(msg.body)
        await support_feedback_request_handler(event, redis=redis)

    else:
        raise ValueError(f"Unknown support response event: {event_name}")