from contextlib import contextmanager
import os
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from app.config import get_database_url, DB_TYPE

_engine = None
_SessionFactory = None


def protect_local_database_file() -> None:
    """Restrict the SQLite database to the interactive OS account where possible."""
    if DB_TYPE != "sqlite":
        return
    db_path = Path(get_database_url().replace("sqlite:///", ""))
    if not db_path.exists():
        return
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    if os.name == "nt":
        username = os.environ.get("USERNAME")
        if username:
            try:
                subprocess.run(
                    ["icacls", str(db_path), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                    check=False, capture_output=True, text=True, timeout=10
                )
            except (OSError, subprocess.SubprocessError):
                pass


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
