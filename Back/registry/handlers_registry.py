# Back/registry/handlers_registry

from Back.core.events_bus.handler_manager import handler_manager

# system
from Back.modules.system.handlers import ping_handler
from Back.modules.system.events import PingEvent
handler_manager.register(PingEvent, ping_handler)

# chat
from Back.modules.chat.handlers import message_handler, restore_handler
from Back.modules.chat.events import NewMessageEvent, GenerationRestoreEvent, NewTokenEvent

handler_manager.register(NewMessageEvent, message_handler)
handler_manager.register(GenerationRestoreEvent, restore_handler)

# handlers_registry.py
from Back.core.events_bus.handler_manager import handler_manager
from Back.modules.support.events import (
    SupportRequestEvent,
    SupportMessageEvent,
    EndSupportDialogEvent,
    UserFeedbackResponseEvent,
)
from Back.modules.support.handlers import (
    ask_support_handler,
    support_send_message_handler,
    end_support_dialog_client_handler,
    support_feedback_handler,
)

handler_manager.register(SupportRequestEvent, ask_support_handler)
handler_manager.register(SupportMessageEvent, support_send_message_handler)
handler_manager.register(EndSupportDialogEvent, end_support_dialog_client_handler)
handler_manager.register(UserFeedbackResponseEvent, support_feedback_handler)