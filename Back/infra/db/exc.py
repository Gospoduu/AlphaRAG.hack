# infra/db/exc.py

from sqlalchemy.exc import OperationalError, DisconnectionError

_DB_RETRYABLE = (
    OperationalError,
    DisconnectionError,
)