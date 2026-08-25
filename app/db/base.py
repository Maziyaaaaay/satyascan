import uuid
from typing import Any, Optional

from sqlalchemy import CHAR, TypeDecorator, event
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses Postgres's native UUID type when available, otherwise stores as a
    stringified CHAR(36) (SQLite, and any other dialect). Lets the same model
    definitions run unchanged against SQLite in dev and Postgres in production.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Optional[Any], dialect: Dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value: Optional[Any], dialect: Dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        is_sqlite = settings.database_url.startswith("sqlite")
        # Webhook dedup claims (see WebhookEvent) open a second connection to
        # this same file concurrently with the per-request session, and
        # SQLite's default rollback-journal mode blocks writers against each
        # other with no wait - a second near-simultaneous write fails
        # immediately with "database is locked" instead of just queuing.
        # WAL mode lets readers/writers coexist, and busy_timeout makes a
        # genuine writer-vs-writer collision wait briefly instead of erroring.
        connect_args = {"timeout": 15} if is_sqlite else {}
        _engine = create_async_engine(settings.database_url, echo=False, future=True, connect_args=connect_args)
        if is_sqlite:

            @event.listens_for(_engine.sync_engine, "connect")
            def _set_sqlite_pragmas(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=15000")
                cursor.close()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def reset_engine_for_tests() -> None:
    """Force get_engine()/get_session_factory() to rebuild against the current
    DATABASE_URL. Used by tests that point at an isolated temp SQLite file."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
    get_settings.cache_clear()
