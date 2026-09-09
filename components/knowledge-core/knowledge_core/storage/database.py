from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from knowledge_core.config import Settings
from knowledge_core.storage.models import Base


def create_database_engine(
    database_url: str,
    *,
    sqlite_test_mode: bool = False,
) -> Engine:
    options: dict[str, object] = {"future": True}
    if sqlite_test_mode:
        options["execution_options"] = {"schema_translate_map": {"kc": None}}
    engine = create_engine(database_url, **options)

    if sqlite_test_mode:
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def create_test_schema(engine: Engine) -> None:
    """Create Task 1 tables for unit tests only; production uses Alembic."""
    Base.metadata.create_all(engine)


def engine_from_environment() -> Engine:
    return create_database_engine(Settings.from_env().database_url)
