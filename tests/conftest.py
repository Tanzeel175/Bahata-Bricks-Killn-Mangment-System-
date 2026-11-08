import os
import pytest
from pathlib import Path

# Force isolated test database file BEFORE any app modules load
TEST_DB_PATH = Path(__file__).resolve().parent / "bahta_test.db"
os.environ["BAHTA_SQLITE_PATH"] = str(TEST_DB_PATH)
# Sample business records remain available to tests, while production seeding stays opt-in.
os.environ["BAHTA_SEED_DEMO_DATA"] = "true"

# Configure app config and database connection to use test database
import app.config
app.config.SQLITE_PATH = str(TEST_DB_PATH)

from app.database import connection
connection._engine = None
connection._SessionFactory = None


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test suite strictly operates on tests/bahta_test.db."""
    yield
    # Cleanup connection pool after test session ends
    if connection._engine:
        connection._engine.dispose()
        connection._engine = None
        connection._SessionFactory = None


def seed_test_auth():
    from app.database.connection import get_db_session
    from app.database.schema import User, Role
    from app.security.hashing import hash_password
    with get_db_session() as session:
        admin_role = session.query(Role).filter_by(RoleName="Administrator").first()
        munshi_role = session.query(Role).filter_by(RoleName="Munshi").first()
        if not session.query(User).filter_by(Username="admin").first():
            session.add(User(
                Username="admin", FullName="Admin",
                PasswordHash=hash_password("Admin@123"),
                RoleID=admin_role.RoleID, IsActive=True
            ))
        if not session.query(User).filter_by(Username="munshi").first():
            session.add(User(
                Username="munshi", FullName="Munshi",
                PasswordHash=hash_password("Munshi@123"),
                RoleID=munshi_role.RoleID, IsActive=True
            ))

