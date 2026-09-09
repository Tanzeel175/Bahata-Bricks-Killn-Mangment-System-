from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from app.config import get_database_url

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = get_database_url()
        connect_args = {}
        engine_kwargs = {"echo": False}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False, "timeout": 30}
            engine_kwargs["connect_args"] = connect_args
            # Use NullPool for SQLite to prevent stale cached in-memory DBAPI connections
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_pre_ping"] = True

        _engine = create_engine(db_url, **engine_kwargs)

        if db_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=15000")
                cursor.close()

    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
    return _SessionFactory


@contextmanager
def get_db_session():
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        session_factory.remove()
