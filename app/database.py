from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None
_configured_database_url: Optional[str] = None


def get_engine() -> Engine:
    global _configured_database_url, _engine, _session_factory

    database_url = get_settings().database_url
    if _engine is None or _configured_database_url != database_url:
        _engine = create_engine(
            database_url,
            connect_args=_sqlite_connect_args(database_url),
        )
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        _configured_database_url = database_url
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
