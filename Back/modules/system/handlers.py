# Back/modules/system/handlers.py

from .events import PingEvent, PongEvent, PongData
from Back.core.events_bus.handler_policy import with_policy
from Back.infra.redis.streams import add_new_emit
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from logging import getLogger

logger = getLogger(__name__)

@with_policy()
async def ping_handler(ping: PingEvent, redis: Redis, db: AsyncSession):
    try:
        pong =  PongEvent(
            data=PongData(
                user_uuid=ping.data.user_uuid,
            )
        )
        await add_new_emit(user_uuid=ping.data.user_uuid, redis=redis, event=pong)
    except Exception:
        logger.exception("Ping handler failed for user %s", ping.data.user_uuid)
        raise
