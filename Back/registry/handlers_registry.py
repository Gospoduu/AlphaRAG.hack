# Back/registry/handlers_registry

from Back.core.events_bus.handler_manager import handler_manager

# system
from Back.modules.system.handlers import ping_handler
from Back.modules.system.events import PingEvent
handler_manager.register(PingEvent, ping_handler)

# chat
from Back.modules.chat.handlers import llm_answer_handler, message_handler, restore_handler
from Back.modules.chat.events import NewMessageEvent, GenerationRestoreEvent, NewTokenEvent

handler_manager.register(NewMessageEvent, message_handler, llm_answer_handler)
handler_manager.register(GenerationRestoreEvent, restore_handler)
