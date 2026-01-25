# Back/core/events_bus/handler_manager

from typing import Callable,  Dict, List, Awaitable, Any
from .events import EventBase
import logging

logger = logging.getLogger(__name__)

HandlerType = Callable[[EventBase], Awaitable[Any]]


class HandlerManager:
    def __init__(self):
        self.__events_dict : Dict[str, List[HandlerType]] = {}
        logger.info(f"Handler manager initialized")
    def register(self, event: str, *handlers: HandlerType):
        if not handlers:
            raise ValueError("At least one handler must be provided")
        if event in self.__events_dict:
            raise KeyError(f"Event `{event}` already registered")
        self.__events_dict[event] = list(handlers)
        logger.info(f"Registered {event} handlers for {len(handlers)} events ")
    def get(self, event: str) -> List[HandlerType]:
        return list(self.__events_dict.get(event, []))
    def __getitem__(self, event: str) -> List[HandlerType]:
        if event not in self.__events_dict:
            raise KeyError(f"Event `{event}` not registered")
        return list(self.__events_dict[event])
    def __contains__(self, event: str) -> bool:
        return event in self.__events_dict

handler_manager = HandlerManager()

