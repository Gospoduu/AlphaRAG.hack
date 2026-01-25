# Back/registry/events_registry.py

from Back.core.events_bus.event_manager import event_manager

# system
from Back.modules.system.events import PingEvent
from Back.core.events_bus.events import ErrorEvent
event_manager.register(ErrorEvent)
event_manager.register(PingEvent)

# chat
from Back.modules.chat.events import NewMessageEvent,NewTokenEvent, EndGenerationEvent, NewMessageResponseEvent, GenerationRestoreEvent, GeneratedTextEvent
event_manager.register(GenerationRestoreEvent)
event_manager.register(GeneratedTextEvent)
event_manager.register(NewMessageEvent)
event_manager.register(NewTokenEvent)
event_manager.register(EndGenerationEvent)
event_manager.register(NewMessageResponseEvent)

