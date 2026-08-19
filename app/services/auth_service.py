import json
import logging
from typing import Tuple, Optional, Dict, Any
from app.database.connection import get_db_session
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.security.hashing import verify_password
from app.security.session import current_session
from app.config import USER_PREFS_FILE

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication, lockout evaluation, and login security."""

    @staticmethod
    def authenticate(username: str, password: str) -> Tuple[bool, str]:
        if not username or not password:
            return False, "Username and Password are required."

        username = username.strip()

        with get_db_session() as session:
            user_repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = user_repo.get_by_username(username)
            if not user:
                audit_repo.log_event("LOGIN_FAILED", username=username, details="User not found")
                return False, "Invalid username or password."

            if not user.IsActive:
                audit_repo.log_event("LOGIN_FAILED", username=username, user_id=user.UserID, details="Inactive account")
                return False, "Account is disabled. Please contact the Administrator."

            if user.IsLocked:
                audit_repo.log_event("LOGIN_FAILED", username=username, user_id=user.UserID, details="Locked account attempt")
                return False, "Account is locked due to multiple failed login attempts. Please contact Administrator to unlock."

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
                    return False, "Account has been locked due to 5 consecutive failed login attempts."
                else:
                    remaining = 5 - user.FailedAttempts
                    audit_repo.log_event(
                        "LOGIN_FAILED",
                        username=username,
                        user_id=user.UserID,
                        details=f"Incorrect password. Failed attempt {user.FailedAttempts}/5"
                    )
                    return False, f"Invalid username or password. {remaining} attempt(s) remaining before lockout."

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
            with open(USER_PREFS_FILE, "w") as f:
                json.dump(prefs, f)
        except Exception as e:
            logger.warning(f"Could not save remembered username: {e}")

    @staticmethod
    def get_remembered_username() -> str:
        try:
            if USER_PREFS_FILE.exists():
                with open(USER_PREFS_FILE, "r") as f:
                    prefs = json.load(f)
                    return prefs.get("remembered_username", "")
        except Exception:
            pass
        return ""
