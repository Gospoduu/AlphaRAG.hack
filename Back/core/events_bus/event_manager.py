# core/event_bus/event_manager

from Back.core.events_bus.events import EventBase
from typing import Dict, Type

class EventManager:
    def __init__(self):
        self.__events_dict: Dict[str, Type[EventBase]] = {}
    def register(self, event_cls: Type[EventBase]):
        if event_cls.event == "":
            raise KeyError(f"Event `{event_cls.__name__}` must not be empty!")
        if event_cls.event in self.__events_dict:
            raise KeyError(f"Event `{event_cls.event}` already registered")
        self.__events_dict[event_cls.event] = event_cls
    def __getitem__(self, event: str) -> Type[EventBase]:
        if event not in self.__events_dict:
            raise KeyError(f"Event `{event}` not found")
        return self.__events_dict[event]
    def get(self, event: str) -> Type[EventBase]|None:
        return self.__events_dict.get(event)
    def __contains__(self, event: str) -> bool:
        return event in self.__events_dict

    def list_events(self):
        return list(self.__events_dict.keys())


event_manager = EventManager()