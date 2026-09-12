import logging
import os

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from Back.infra.kafka.broker import broker
from Back.modules.support.events import (
    SupportRequestEvent,
    SupportMessageEvent,
    EndSupportDialogEvent,
    UserFeedbackResponseEvent,
)
from Back.constants import (
    SUPPORT_REQUEST,
    SUPPORT_MESSAGE,
    END_SUPPORT_DIALOG_REQUEST,
    USER_FEEDBACK_RESPONSE,
)

logger = logging.getLogger(__name__)

SUPPORT_REQUEST_TOPIC = os.getenv("SUPPORT_REQUEST_TOPIC")
if not SUPPORT_REQUEST_TOPIC:
    raise RuntimeError("SUPPORT_REQUEST_TOPIC is not configured")


async def publish_to_support_request_topic(event, event_name: str) -> None:
    await broker.publish(
        event.to_json(),
        topic=SUPPORT_REQUEST_TOPIC,
        headers={"event_name": event_name},
    )


# все четыре хендлера просто форвардят событие в support-service по Kafka -
# сам сапорт-сервис пишет в свою БД, чат-сервису локально ничего хранить не нужно,
# фронт дальше читает состояние через REST-ручки сапорт-сервиса

async def ask_support_handler(event: SupportRequestEvent, redis: Redis, db: AsyncSession) -> None:
    try:
        await publish_to_support_request_topic(event, SUPPORT_REQUEST)
    except Exception:
        logger.error("Failed to publish SUPPORT_REQUEST for user %s", event.data.user_uuid, exc_info=True)
        raise


async def support_send_message_handler(event: SupportMessageEvent, redis: Redis, db: AsyncSession) -> None:
    try:
        await publish_to_support_request_topic(event, SUPPORT_MESSAGE)
    except Exception:
        logger.error("Failed to publish SUPPORT_MESSAGE for user %s", event.data.user_uuid, exc_info=True)
        raise


async def end_support_dialog_client_handler(event: EndSupportDialogEvent, redis: Redis, db: AsyncSession) -> None:
    try:
        await publish_to_support_request_topic(event, END_SUPPORT_DIALOG_REQUEST)
    except Exception:
        logger.error("Failed to publish END_SUPPORT_DIALOG_REQUEST for user %s", event.data.user_uuid, exc_info=True)
        raise


async def support_feedback_handler(event: UserFeedbackResponseEvent, redis: Redis, db: AsyncSession) -> None:
    try:
        await publish_to_support_request_topic(event, USER_FEEDBACK_RESPONSE)
    except Exception:
        logger.error("Failed to publish USER_FEEDBACK_RESPONSE for user %s", event.data.user_uuid, exc_info=True)
        raise