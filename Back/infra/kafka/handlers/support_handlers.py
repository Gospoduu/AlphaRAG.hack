import logging

from redis.asyncio import Redis

from Back.infra.redis.streams import add_new_emit
from Back.modules.support.events import (
    SupportResponseEvent,
    SupportMessageEvent,
    UpdateDialogStatusEvent,
    UserFeedbackRequestEvent,
)

logger = logging.getLogger(__name__)


async def support_response_handler(event: SupportResponseEvent, redis: Redis) -> None:
    # диалог создан, специалист назначен - фронт по этому событию идёт
    # за деталями через GET /supporters/{dialog_id} и GET /dialogs/user/{user_id}
    try:
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error("Failed to emit SUPPORT_RESPONSE for user %s", event.data.user_uuid, exc_info=True)
        raise


async def support_message_handler(event: SupportMessageEvent, redis: Redis) -> None:
    try:
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error("Failed to emit SUPPORT_MESSAGE for user %s", event.data.user_uuid, exc_info=True)
        raise


async def support_status_changed_handler(event: UpdateDialogStatusEvent, redis: Redis) -> None:
    try:
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error("Failed to emit UPDATE_DIALOG_STATUS for user %s", event.data.user_uuid, exc_info=True)
        raise


async def support_feedback_request_handler(event: UserFeedbackRequestEvent, redis: Redis) -> None:
    try:
        await add_new_emit(redis=redis, event=event, user_uuid=event.data.user_uuid)
    except Exception:
        logger.error("Failed to emit USER_FEEDBACK_REQUEST for user %s", event.data.user_uuid, exc_info=True)
        raise