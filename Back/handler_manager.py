from typing import Callable, Any, AsyncGenerator, Optional, Dict, List, Coroutine, Union

from .events import ErrorEvent, UnknownEventTypeErrorData, EventBase

HandlerType = Callable[..., Union[EventBase, AsyncGenerator[EventBase, None], Coroutine[Any, Any, EventBase]]]

class HandlerManager:
    def __init__(self):
        self.events_dict : Dict[str, List[HandlerType]] = {}
    def register(self, event: str, *handlers: HandlerType):
        self.events_dict[event] = list(handlers)
        print(f"Registered {event} handlers for {handlers.__ne__} ")
    def get_handlers(self, event: str) -> List[HandlerType]:
        return self.events_dict.get(event, [])
handler_manager = HandlerManager()

