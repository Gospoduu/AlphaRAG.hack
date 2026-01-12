from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from Back.infra.db.db import get_db
from Back.modules.chat.crud import ping_db
from Back.infra.redis.cache_manager import redis_is_fine, get_redis
from Back.modules.user.api import router as user_router
from Back.ws.ws import router as user_ws_router
from Back.modules.chat.api import router as chat_router
from Back.register_handlers import register_all_handlers
from Back.core.events_bus.handler_manager import handler_manager
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="back/static"), name="static")

# Пример маршрута для проверки
@app.get("/")
async def read_root():
    return {"message": "API работает!"}

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
    print("ROUTE:", route.path, getattr(route, "methods", None), type(route))

if __name__ == "__main__":
    register_all_handlers(handler_manager)
    uvicorn.run("Back.main.main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                reload_dirs=["Back/"])