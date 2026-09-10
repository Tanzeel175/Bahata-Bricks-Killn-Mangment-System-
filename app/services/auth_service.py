import json
import logging
import os
import tempfile
from typing import Tuple, Optional, Dict, Any
from app.database.connection import get_db_session
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.database.schema import User, Role
from app.security.hashing import verify_password, hash_password
from app.security.session import current_session
from app.security.rbac import require_authenticated
from app.config import USER_PREFS_FILE
from app.validators.user_validator import validate_username, validate_password_strength

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication, lockout evaluation, and login security."""

    @staticmethod
    def authenticate(username: str, password: str) -> Tuple[bool, str]:
        if not username or not password:
            return False, "Username and Password are required."

        username = username.strip()

        if len(password) > 128:
            return False, "Invalid username or password."

        with get_db_session() as session:
            user_repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = user_repo.get_by_username(username)
            if not user:
                # Maintain bcrypt work for unknown users to reduce account-enumeration timing leaks.
                verify_password(password, "$2b$12$LQv3c1W2dM/1oMZfAVC8EOx1bZlG9Sg6aC3HWfU6eLxg6DBUMg5YG")
                audit_repo.log_event("LOGIN_FAILED", username=username, details="User not found")
                return False, "Invalid username or password."

            if not user.IsActive:
                audit_repo.log_event("LOGIN_FAILED", username=username, user_id=user.UserID, details="Inactive account")
                return False, "Invalid username or password."

            if user.IsLocked:
                audit_repo.log_event("LOGIN_FAILED", username=username, user_id=user.UserID, details="Locked account attempt")
                return False, "Invalid username or password."

            # Password check
            if not verify_password(password, user.PasswordHash):
                is_locked = user_repo.increment_failed_attempts(user)
                if is_locked:
                    audit_repo.log_event(
                        "ACCOUNT_LOCKED",
                        username=username,
                        user_id=user.UserID,
                        details="Account locked after 5 failed attempts"
                    )
                    return False, "Invalid username or password."
                else:
                    remaining = 5 - user.FailedAttempts
                    audit_repo.log_event(
                        "LOGIN_FAILED",
                        username=username,
                        user_id=user.UserID,
                        details=f"Incorrect password. Failed attempt {user.FailedAttempts}/5"
                    )
                    return False, "Invalid username or password."

            # Successful login
            user_repo.update_last_login(user)
            role_name = user.role.RoleName if user.role else "Munshi"
            
            current_session.login(
                user_id=user.UserID,
                username=user.Username,
                full_name=user.FullName,
                role_name=role_name
            )

            audit_repo.log_event(
                "LOGIN_SUCCESS",
                username=username,
                user_id=user.UserID,
                details=f"Login successful as role '{role_name}'"
            )

            return True, "Login successful."

    @staticmethod
    def logout():
        if current_session.is_authenticated:
            uname = current_session.username
            uid = current_session.user_id
            with get_db_session() as session:
                audit_repo = AuditRepository(session)
                audit_repo.log_event("LOGOUT", username=uname, user_id=uid, details="User logged out")
            current_session.logout()

    @staticmethod
    def needs_initial_setup() -> bool:
        """Return whether this database has no user account yet."""
        with get_db_session() as session:
            return session.query(User).count() == 0

    @staticmethod
    def create_initial_administrator(username: str, full_name: str, password: str) -> Tuple[bool, str]:
        """Create the sole first administrator. This is allowed only for a blank user table."""
        valid_username, username_error = validate_username(username)
        if not valid_username:
            return False, username_error
        valid_password, password_errors = validate_password_strength(password)
        if not valid_password:
            return False, "\n".join(password_errors)
        if not full_name or not full_name.strip():
            return False, "Full name is required."

        with get_db_session() as session:
            if session.query(User).count() != 0:
                return False, "Initial setup is already complete."
            admin_role = session.query(Role).filter_by(RoleName="Administrator").first()
            if not admin_role:
                return False, "Administrator role is missing. Restart the application to repair the database."
            user = User(
                Username=username.strip(),
                PasswordHash=hash_password(password),
                FullName=full_name.strip(),
                RoleID=admin_role.RoleID,
                IsActive=True,
                IsLocked=False,
                CreatedBy="INITIAL_SETUP"
            )
            session.add(user)
            session.flush()
            AuditRepository(session).log_event(
                "INITIAL_ADMIN_CREATED", username=user.Username, user_id=user.UserID,
                details="First administrator was created through secure initial setup."
            )
            return True, "Administrator account created. Please sign in."

    @staticmethod
    @require_authenticated
    def requires_password_change() -> bool:
        with get_db_session() as session:
            user = session.get(User, current_session.user_id)
            return bool(user and user.MustChangePassword)

    @staticmethod
    @require_authenticated
    def change_own_password(new_password: str) -> Tuple[bool, str]:
        valid, errors = validate_password_strength(new_password)
        if not valid:
            return False, "\n".join(errors)
        with get_db_session() as session:
            user = session.get(User, current_session.user_id)
            if not user:
                return False, "Your session is no longer valid."
            user.PasswordHash = hash_password(new_password)
            user.MustChangePassword = False
            user.FailedAttempts = 0
            user.IsLocked = False
            AuditRepository(session).log_event(
                "PASSWORD_CHANGED", username=user.Username, user_id=user.UserID,
                details="User changed password during secure credential upgrade."
            )
        return True, "Password updated."

    @staticmethod
    def save_remembered_username(username: str):
        try:
            prefs = {}
            if USER_PREFS_FILE.exists():
                try:
                    with open(USER_PREFS_FILE, "r") as f:
                        prefs = json.load(f)
                except Exception:
                    prefs = {}
            prefs["remembered_username"] = username
            USER_PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(prefix=".prefs-", dir=USER_PREFS_FILE.parent, text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(prefs, f)
                os.replace(temp_path, USER_PREFS_FILE)
                try:
                    os.chmod(USER_PREFS_FILE, 0o600)
                except OSError:
                    pass
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Could not save remembered username: {e}")

    @staticmethod
    def get_remembered_username() -> str:
        try:
            if USER_PREFS_FILE.exists():
                with open(USER_PREFS_FILE, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                    return prefs.get("remembered_username", "")
        except Exception:
            pass
        return ""
