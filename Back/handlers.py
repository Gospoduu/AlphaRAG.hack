from events import PingEvent, PongEvent

async def ping_handler(ping: PingEvent):
    return PongEvent()
