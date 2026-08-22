import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from pathlib import Path

import openai

PROJECT_ROOT = Path(__file__).resolve().parents[3]
env_path = PROJECT_ROOT / ".env"
print("🔍 Ищу .env по пути:", env_path)
load_dotenv(dotenv_path=env_path)

YANDEX_FOLDER_ID=os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY=os.getenv("YANDEX_API_KEY")

client = openai.AsyncOpenAI(
    api_key=YANDEX_API_KEY,
    project=YANDEX_FOLDER_ID,
    base_url="https://ai.api.cloud.yandex.net/v1"
)

# Обработка потоковых событий (зависит от формата ответа)
async def get_ans_from_yandex(query: str) -> AsyncGenerator:
    response = await client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/gpt-oss-120b",
        instructions="Ты креативный ассистент...",
        input=query,
        reasoning={"effort": "low"},
        temperature=0.0,
        max_output_tokens=4000,
        stream=True
    )
    async for token in response:
        if token.type == "response.output_text.delta":
            yield token.delta
    yield "\n Ans done."