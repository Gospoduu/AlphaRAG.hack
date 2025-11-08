from start_redis import redis_client
from redis.asyncio import Redis
from typing import AsyncGenerator

async def get_redis()->AsyncGenerator[Redis]:
    yield redis_client

async def add_active_user(user_uuid: str, redis: Redis):
    await redis.sadd("active_users",user_uuid)

async def delete_active_user(user_uuid: str, redis: Redis):
    await redis.srem("active_users", user_uuid)

async def add_active_operator(operator_uuid: str, redis: Redis):
    await redis.sadd("active_operators", operator_uuid)

async def delete_active_operator(operator_uuid: str, redis: Redis):
    await redis.srem("active_operators", operator_uuid)

async def add_generated_token(token: str, chat_id: int, redis: Redis):
    key = f"chat:{chat_id}:generated_text"
    await redis.append(key, token)
    await redis.expire(key, 60*60*24)

async def delete_generated_text(chat_id: int, redis: Redis):
    key = f"chat:{chat_id}:generated_text"
    await redis.delete(key)