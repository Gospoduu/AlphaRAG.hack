"""Debounced operator offers. Redis owns cancellation and the per-chat cooldown."""
import asyncio
from datetime import datetime, timezone
import logging
import os
from uuid import UUID, uuid4

from sqlalchemy import select

from Back.infra.db.db import AsyncSessionLocal
from Back.infra.redis.streams import add_new_emit
from . import crud
from .events import EndGenerationData, EndGenerationEvent
from .models import Chat, Message, Role

logger = logging.getLogger(__name__)
OFFER_DELAY_SECONDS = 5
OFFER_COOLDOWN_SECONDS = 8 * 60
OFFER_TEXT = 'Похоже, мой ответ не помог. Хотите передать ваш вопрос оператору поддержки?'
_tasks = set()


def pending_key(chat_id):
    return f'chat:{chat_id}:dislike:pending'


def cooldown_key(chat_id):
    return f'chat:{chat_id}:dislike:cooldown'


# Compare and delete so a cancelled worker cannot erase a newer timer.
CANCEL_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if value and (ARGV[1] == '' or string.sub(value, 1, string.len(ARGV[1])) == ARGV[1]) then
  return redis.call('DEL', KEYS[1])
end
return 0
"""
CLAIM_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('DEL', KEYS[1])
return redis.call('SET', KEYS[2], '1', 'NX', 'EX', ARGV[2]) and 1 or 0
"""


async def cancel_operator_offer(chat_id, redis, message_id=None):
    try:
        prefix = '' if message_id is None else f'{message_id}:'
        await redis.eval(CANCEL_SCRIPT, 1, pending_key(chat_id), prefix)
    except Exception:
        logger.exception('Could not cancel operator offer for chat %s', chat_id)


async def schedule_operator_offer(chat_id, message_id, user_uuid, redis):
    token = f'{message_id}:{uuid4()}'
    try:
        if await redis.get(cooldown_key(chat_id)):
            return
        if not await redis.set(pending_key(chat_id), token, nx=True, ex=60):
            return
        task = asyncio.create_task(_send_operator_offer_after_delay(
            redis, chat_id, message_id, user_uuid, token,
            datetime.now(timezone.utc).isoformat(),
        ))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    except Exception:
        logger.exception('Could not schedule operator offer for chat %s', chat_id)


async def _send_operator_offer_after_delay(redis, chat_id, message_id, user_uuid, token, requested_at):
    try:
        await asyncio.sleep(OFFER_DELAY_SECONDS)
        # This session belongs to the worker, not to the completed HTTP request.
        async with AsyncSessionLocal() as db:
            chat = await db.get(Chat, chat_id)
            message = await db.get(Message, message_id)
            if (chat is None or message is None or chat.user_uuid != user_uuid
                    or message.chat_id != chat_id or message.reaction != -1
                    or chat.is_generate or chat.is_blocked):
                return
            question = await db.scalar(select(Message).where(
                Message.chat_id == chat_id, Message.user_role == Role.USER
            ).order_by(Message.local_id.desc()).limit(1))
            if question is None or question.local_id > message.local_id:
                return  # The user already continued this conversation.
            if not await redis.eval(CLAIM_SCRIPT, 2, pending_key(chat_id),
                                    cooldown_key(chat_id), token, OFFER_COOLDOWN_SECONDS):
                return
            local_id = (await crud.get_last_message_local_id(db, chat_id) or 0) + 1
            offer = await crud.create_message(
                db=db, chat_id=chat_id, text=OFFER_TEXT,
                user_uuid=UUID(os.environ['LLM_USER_UUID']), user_role=Role.BOT,
                answered_to=message_id, local_id=local_id,
            )
            await db.commit()
            # No token stream and no generation-state changes: this is an offer,
            # not another LLM generation competing with the user's next question.
            event = EndGenerationEvent(
                data=EndGenerationData(chat_id=chat_id, user_uuid=user_uuid,
                                       details='is_user_need_support', all_text=OFFER_TEXT),
                meta={'is_user_need_support': True, 'message_id': offer.id,
                      'user_query': question.text, 'offer_requested_at': requested_at},
            )
            await add_new_emit(redis=redis, event=event, user_uuid=user_uuid)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception('Could not send operator offer for chat %s', chat_id)
    finally:
        try:
            await redis.eval(CANCEL_SCRIPT, 1, pending_key(chat_id), token)
        except Exception:
            logger.exception('Could not clean up operator offer timer for chat %s', chat_id)
