import pytest
from app.database.init_db import init_db
from app.services.auth_service import AuthService
from app.security.hashing import hash_password, verify_password
from app.security.session import current_session


@pytest.fixture(autouse=True)
def setup_database():
    from app.database.schema import Base
    from app.database.connection import get_engine
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    current_session.logout()



def test_bcrypt_hashing():
    pw = "Secret@123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("Wrong@123", hashed) is False


def test_login_success_admin():
    success, msg = AuthService.authenticate("admin", "Admin@123")
    assert success is True
    assert "successful" in msg
    assert current_session.is_authenticated is True
    assert current_session.username == "admin"
    assert current_session.is_admin is True
    AuthService.logout()


def test_login_success_munshi():
    success, msg = AuthService.authenticate("munshi", "Munshi@123")
    assert success is True
    assert current_session.username == "munshi"
    assert current_session.is_munshi is True
    AuthService.logout()


def test_login_invalid_credentials():
    success, msg = AuthService.authenticate("admin", "WrongPassword")
    assert success is False
    assert "Invalid" in msg or "attempt" in msg


def test_account_lockout_after_5_failed_attempts():
    username = "munshi"
    # Execute 5 incorrect login attempts
    for i in range(5):
        AuthService.authenticate(username, "WrongPassword")

    # 6th attempt should reflect locked state
    success, msg = AuthService.authenticate(username, "WrongPassword")
    assert success is False
    assert "locked" in msg.lower()
