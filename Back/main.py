# Back/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from Back.infra.db.db import get_db
from Back.modules.chat.crud import ping_db
from Back.infra.redis.cache_manager import redis_is_fine, get_redis
from Back.modules.user.api import router as user_router
from Back.ws.ws import router as user_ws_router
from Back.modules.chat.api import router as chat_router
import Back.registry.handlers_registry
import Back.registry.events_registry
from logging import getLogger
from pathlib import Path
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent  # .../Back
STATIC_DIR = BASE_DIR / "static"


logger = getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Пример маршрута для проверки
@app.get("/")
async def read_root():
    return FileResponse(STATIC_DIR / "index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем доступ только с порта 63342
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

app.include_router(user_router, tags=["user"], prefix="/api")
app.include_router(user_ws_router,tags=["ws"],  prefix="/api")
app.include_router(chat_router,tags=["chat"], prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
@app.get("/api/redis/ping")
async def redis_ping(r: Redis = Depends(get_redis)):
    status = "ok" if await redis_is_fine(r) else "error"
    return {"redis": status}
@app.get("/api/db/ping")
async def db_ping(db: AsyncSession = Depends(get_db)):
    status = "ok" if await ping_db(db) else "error"
    return {"db": status}

for route in app.routes:
    logger.debug("ROUTE: %s %s %s", route.path, getattr(route, "methods", None), type(route))