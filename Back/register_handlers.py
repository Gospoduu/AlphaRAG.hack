from .handler_manager import HandlerManager
from .events import PongEvent, PingEvent
from .handlers import ping_handler
from .chat.events import NewMessageEvent
from .chat.handlers import message_handler, llm_answer_handler

def register_all_handlers(handler_manager: HandlerManager):


    handler_manager.register(
        PingEvent.model_fields["event"].default,
        ping_handler
    )
    print("Ping handler registered", PingEvent.model_fields["event"].default)

    handler_manager.register(
        NewMessageEvent.model_fields["event"].default,
        message_handler,
        llm_answer_handler
    )
    print("New message handler registered", NewMessageEvent.model_fields["event"].default)
