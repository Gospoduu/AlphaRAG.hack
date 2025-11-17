from .events import PingEvent, PongEvent
from .handler_manager import handler_manager

async def ping_handler(ping: PingEvent):
    return PongEvent(
        status="ok"
    )


handler_manager.register("ping", ping_handler)