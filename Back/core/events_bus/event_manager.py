# core/event_bus/event_manager
from pydantic_core import PydanticUndefined
from Back.core.events_bus.events import EventBase
from typing import Dict, Type

class EventManager:
    def __init__(self):
        self.__events_dict: Dict[str, Type[EventBase]] = {}
    def register(self, event_cls: Type[EventBase]):
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
        self.__events_dict[event_name.strip().upper()] = event_cls
    def __getitem__(self, event: str) -> Type[EventBase]:
        if event not in self.__events_dict:
            raise KeyError(f"Event `{event}` not found")
        return self.__events_dict[event]
    def get(self, event: str) -> Type[EventBase]|None:
        return self.__events_dict.get(event.strip().upper())
    def __contains__(self, event: str) -> bool:
        return event in self.__events_dict

    def list_events(self):
        return list(self.__events_dict.keys())


event_manager = EventManager()