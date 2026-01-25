# Back/core/events_bus/handler_policy

from dataclasses import dataclass

@dataclass(frozen=True)
class HandlerPolicy:
    retry: bool=False
    try_cnt: int=3
    delay: float=2

    def to_dict(self):
        return {
            "retry": self.retry,
            "try_cnt": self.try_cnt,
            "delay": self.delay
        }

DEFAULT_POLICY: HandlerPolicy = HandlerPolicy()

def with_policy(**kwargs):
    policy = HandlerPolicy(**{**DEFAULT_POLICY.to_dict(),**kwargs})
    def wrapper(func):
        setattr(func, "__policy__", policy)
        return func
    return wrapper

def get_policy(handler):
    return getattr(handler, "__policy__", DEFAULT_POLICY)
