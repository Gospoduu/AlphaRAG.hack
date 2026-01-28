# Back/core/events_bus/handler_manager
from pydantic_core import PydanticUndefined
from typing import Callable,  Dict, List, Awaitable, Any, Type
from .events import EventBase
import logging

logger = logging.getLogger(__name__)

HandlerType = Callable[[EventBase], Awaitable[Any]]


class HandlerManager:
    def __init__(self):
        self.__events_dict : Dict[str, List[HandlerType]] = {}
        logger.info(f"Handler manager initialized")
    def register(self, event_cls: Type[EventBase], *handlers: HandlerType):
        field = event_cls.model_fields.get("event")
        if field is None:
            raise KeyError(f"Event `{event_cls.__name__}` must not be empty!")
        event_name = field.default
        if event_name is PydanticUndefined or not isinstance(event_name, str) or not event_name.strip():
            raise KeyError(
                f"Event `{event_cls.__name__}` must have non-empty default `event` "
                f"(e.g. event: str = 'ping')"
            )
        if event_name in self.__events_dict:
            raise KeyError(f"Event `{event_name}` already registered")
        if not handlers:
            raise ValueError("At least one handler must be provided")
        if event_name in self.__events_dict:
            raise KeyError(f"Event `{event_name}` already registered")
        self.__events_dict[event_name] = list(handlers)
        logger.info(f"Registered {event_name} handlers for {len(handlers)} events ")
    def get(self, event: str) -> List[HandlerType]:
        return list(self.__events_dict.get(event, []))
    def __getitem__(self, event: str) -> List[HandlerType]:
        if event not in self.__events_dict:
            raise KeyError(f"Event `{event}` not registered")
        return list(self.__events_dict[event])
    def __contains__(self, event: str) -> bool:
        return event in self.__events_dict

handler_manager = HandlerManager()

