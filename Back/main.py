# Back/main.py


from logging import getLogger
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from Back.modules.chat.metrics import HttpMetricsMiddleware, router as metrics_router, ws_commands
from Back.modules.chat.crud import ping_db
from Back.infra.db.start_db import init_db
from Back.infra.db.db import get_db
from Back.infra.redis.cache_manager import redis_is_fine, get_redis
from Back.infra.kafka.broker import broker
from Back.modules.user.api import router as user_router
from Back.ws.ws import router as user_ws_router
from Back.modules.chat.api import router as chat_router

# These imports register events, command handlers and Kafka subscriptions.
# Keep them before metrics initialization and broker.start().
import Back.registry.events_registry  # noqa: F401
import Back.registry.handlers_registry  # noqa: F401
import Back.infra.kafka.subscribers  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent  # .../Back
STATIC_DIR = BASE_DIR / "static"


logger = getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await broker.start()
    try:
        yield
    finally:
        await broker.stop()

app = FastAPI(lifespan=lifespan)
app.add_middleware(HttpMetricsMiddleware)
app.include_router(metrics_router)
# Initialize registered event series before the first scrape.
from Back.core.events_bus.event_manager import event_manager
for event_name in event_manager.list_events():
    if event_name != 'PING':
        ws_commands.labels(event_name)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

import httpx
from fastapi.responses import Response

media_mounted = False
for _cand in [
    BASE_DIR.parent / "dataset" / "media",
    BASE_DIR.parent / "dataset" / "knowledgebase_mos_ru" / "media",
    Path("/app/dataset/media"),
    Path("/app/dataset/knowledgebase_mos_ru/media"),
    Path("/Users/todaisy/rlt_project/dataset/media"),
    Path("/Users/todaisy/rlt_project/dataset/knowledgebase_mos_ru/media"),
]:
    if _cand.exists():
        app.mount("/media", StaticFiles(directory=_cand), name="media")
        logger.info(f"Mounted /media from {_cand}")
        media_mounted = True
        break

if not media_mounted:
    @app.get("/media/{file_path:path}")
    async def proxy_media(file_path: str):
        for host in ["http://localhost:8001", "http://127.0.0.1:8001", "http://host.docker.internal:8001"]:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{host}/media/{file_path}")
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "image/png")
                        return Response(content=resp.content, media_type=content_type)
            except Exception:
                continue
        return Response(status_code=404)


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
