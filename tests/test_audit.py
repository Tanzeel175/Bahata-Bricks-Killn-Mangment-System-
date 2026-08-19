import pytest
from app.database.init_db import init_db
from app.database.connection import get_db_session
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


@pytest.fixture(autouse=True)
def setup_db_and_auth():
    from app.database.schema import Base
    from app.database.connection import get_engine
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    AuthService.authenticate("admin", "Admin@123")
    yield
    AuthService.logout()


def test_audit_log_creation_and_search():
    with get_db_session() as session:
        repo = AuditRepository(session)
        repo.log_event(action="TEST_ACTION", username="admin", details="Testing audit log creation")

    logs = AuditService.get_audit_logs(query_str="Testing audit log creation")
    assert len(logs) >= 1
    assert logs[0]["Action"] == "TEST_ACTION"
    assert logs[0]["Username"] == "admin"


def test_audit_log_action_filter():
    with get_db_session() as session:
        repo = AuditRepository(session)
        repo.log_event(action="SPECIAL_FILTER_ACTION", username="admin", details="Filter test log")

    logs = AuditService.get_audit_logs(action_filter="SPECIAL_FILTER_ACTION")
    assert len(logs) == 1
    assert logs[0]["Action"] == "SPECIAL_FILTER_ACTION"
