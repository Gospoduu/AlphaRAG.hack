from fastapi import HTTPException
from typing import Optional, Callable
from functools import wraps

def endpoint_try(func: Callable) -> Optional[Callable]:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=f"User not found: {e}")
        except ConnectionError as e:
            raise HTTPException(status_code=408, detail=f"Connection error {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper