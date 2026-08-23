from pathlib import Path
from dotenv import load_dotenv
from logging import getLogger
import os
from Back.infra.kafka.broker import broker
from Back.modules.chat.events import NewMessageEvent

logger = getLogger(__name__)

LLM_REQUEST_TOPIC = os.getenv("LLM_REQUEST_TOPIC")
LLM_RESPONSE_TOPIC = os.getenv("LLM_RESPONSE_TOPIC")

if not LLM_REQUEST_TOPIC:
    raise RuntimeError("LLM_REQUEST_TOPIC is not configured")

async def publish_test_message(message: str) -> None:
    await broker.publish(
        message,
        topic=LLM_REQUEST_TOPIC,
    )

async def publish_message(message: NewMessageEvent) -> None:
    try:
        await broker.publish(
            message,
            topic=LLM_REQUEST_TOPIC,
        )
        logger.info(f"Published message: {message}")
    except Exception as ex:
        logger.error(f"Failed to publish message: {message}: {ex}")