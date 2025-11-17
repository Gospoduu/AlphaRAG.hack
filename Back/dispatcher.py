from types import AsyncGeneratorType, coroutine
import inspect
from Back.chat.events import NewMessageEvent
from .events import EventBase, ErrorEvent, UnknownEventTypeErrorData, HandlerErrorData
from typing import List, AsyncGenerator
from .handler_manager import HandlerManager


async def dispatcher_event(
        handler_manager: HandlerManager,
        event_name: str,
        event_obj: EventBase,
        **context
) -> AsyncGenerator[EventBase]:
    handlers = handler_manager.get_handlers(event_name)
    if not handlers:
        yield ErrorEvent(data=UnknownEventTypeErrorData(details=f"No handlers for event {event_name}"))
    for handler in handlers:
        try:
            sig = inspect.signature(handler)
            kwargs = {k: v for k, v in context.items() if k in sig.parameters}
            result = handler(event_obj, **kwargs)
            if inspect.isasyncgen(result):
                async for event in result:
                    yield event

            elif inspect.isawaitable(result):
                event = await result
                if isinstance(event, EventBase):
                    yield event

            elif isinstance(result, EventBase):
                yield result
        except Exception as e:
            yield ErrorEvent(
                data=HandlerErrorData(details=str(e))
            )
            return




