from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import get_database_url

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = get_database_url()
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False
        )
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
