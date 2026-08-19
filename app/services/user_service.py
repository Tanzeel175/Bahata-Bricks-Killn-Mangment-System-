from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.database.schema import User, AuditLog
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.security.hashing import hash_password
from app.security.rbac import require_admin
from app.security.session import current_session
from app.validators.user_validator import (
    validate_username, validate_password_strength, validate_email
)


class UserService:
    """Service layer for User Management operations (Administrator restricted)."""

    @staticmethod
    @require_admin
    def get_all_users() -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = UserRepository(session)
            users = repo.get_all_with_roles()
            return [
                {
                    "UserID": u.UserID,
                    "Username": u.Username,
                    "FullName": u.FullName,
                    "Role": u.role.RoleName if u.role else "",
                    "RoleID": u.RoleID,
                    "Email": u.Email or "",
                    "Mobile": u.Mobile or "",
                    "IsActive": u.IsActive,
                    "IsLocked": u.IsLocked,
                    "FailedAttempts": u.FailedAttempts,
                    "CreatedBy": u.CreatedBy or "",
                    "CreatedDate": u.CreatedDate.strftime("%Y-%m-%d %H:%M") if u.CreatedDate else "",
                    "LastLogin": u.LastLogin.strftime("%Y-%m-%d %H:%M") if u.LastLogin else "Never"
                }
                for u in users
            ]

    @staticmethod
    @require_admin
    def create_user(data: Dict[str, Any]) -> Tuple[bool, str]:
        username = data.get("Username", "").strip()
        password = data.get("Password", "")
        full_name = data.get("FullName", "").strip()
        role_name = data.get("Role", "Munshi")
        email = data.get("Email", "").strip()
        mobile = data.get("Mobile", "").strip()

        # Validate username
        valid_un, un_err = validate_username(username)
        if not valid_un:
            return False, un_err

        # Validate full name
        if not full_name:
            return False, "Full Name is required."

        # Validate password
        valid_pw, pw_errs = validate_password_strength(password)
        if not valid_pw:
            return False, "\n".join(pw_errs)

        # Validate email
        valid_em, em_err = validate_email(email)
        if not valid_em:
            return False, em_err

        with get_db_session() as session:
            repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            # Check uniqueness
            existing = repo.get_by_username(username)
            if existing:
                return False, f"Username '{username}' already exists. Please choose a different username."

            # Fetch role
            role = repo.get_role_by_name(role_name)
            if not role:
                return False, f"Role '{role_name}' does not exist."

            hashed = hash_password(password)
            new_user = User(
                Username=username,
                PasswordHash=hashed,
                FullName=full_name,
                Email=email if email else None,
                Mobile=mobile if mobile else None,
                RoleID=role.RoleID,
                IsActive=data.get("IsActive", True),
                IsLocked=False,
                CreatedBy=current_session.username
            )
            repo.add(new_user)
            audit_repo.log_event(
                "USER_CREATED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Created user '{username}' with role '{role_name}'"
            )

            return True, f"User '{username}' created successfully."

    @staticmethod
    @require_admin
    def update_user(user_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        with get_db_session() as session:
            repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = repo.get_by_id(user_id)
            if not user:
                return False, "User not found."

            full_name = data.get("FullName", "").strip()
            role_name = data.get("Role", "")
            email = data.get("Email", "").strip()
            mobile = data.get("Mobile", "").strip()
            is_active = data.get("IsActive", True)

            if full_name:
                user.FullName = full_name
            if email:
                valid_em, em_err = validate_email(email)
                if not valid_em:
                    return False, em_err
                user.Email = email

            user.Mobile = mobile if mobile else user.Mobile
            user.IsActive = is_active

            if role_name:
                role = repo.get_role_by_name(role_name)
                if role:
                    user.RoleID = role.RoleID

            repo.update(user)
            audit_repo.log_event(
                "USER_UPDATED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Updated details for user ID {user_id} ('{user.Username}')"
            )

            return True, f"User '{user.Username}' updated successfully."

    @staticmethod
    @require_admin
    def reset_password(user_id: int, new_password: str) -> Tuple[bool, str]:
        valid_pw, pw_errs = validate_password_strength(new_password)
        if not valid_pw:
            return False, "\n".join(pw_errs)

        with get_db_session() as session:
            repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = repo.get_by_id(user_id)
            if not user:
                return False, "User not found."

            user.PasswordHash = hash_password(new_password)
            user.FailedAttempts = 0
            user.IsLocked = False
            repo.update(user)

            audit_repo.log_event(
                "PASSWORD_RESET",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Reset password for user '{user.Username}'"
            )

            return True, f"Password for user '{user.Username}' has been reset."

    @staticmethod
    @require_admin
    def toggle_lock_status(user_id: int, lock: bool) -> Tuple[bool, str]:
        with get_db_session() as session:
            repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = repo.get_by_id(user_id)
            if not user:
                return False, "User not found."

            user.IsLocked = lock
            if not lock:
                user.FailedAttempts = 0
            repo.update(user)

            action = "USER_LOCKED" if lock else "USER_UNLOCKED"
            audit_repo.log_event(
                action,
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"{'Locked' if lock else 'Unlocked'} user '{user.Username}'"
            )

            state_str = "locked" if lock else "unlocked"
            return True, f"User '{user.Username}' has been {state_str}."

    @staticmethod
    @require_admin
    def delete_user(user_id: int) -> Tuple[bool, str]:
        with get_db_session() as session:
            repo = UserRepository(session)
            audit_repo = AuditRepository(session)

            user = repo.get_by_id(user_id)
            if not user:
                return False, "User not found."

            if user.Username == "admin" or user.UserID == current_session.user_id:
                return False, "Cannot delete the default Admin or your own currently logged-in account."

            target_uname = user.Username
            repo.delete(user)

            audit_repo.log_event(
                "USER_DELETED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Deleted user '{target_uname}' (ID: {user_id})"
            )

            return True, f"User '{target_uname}' deleted."

    @staticmethod
    @require_admin
    def get_login_history(username: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            audit_repo = AuditRepository(session)
            if username:
                logs = audit_repo.get_logs_by_user(username)
            else:
                logs = audit_repo.get_recent_logs(100)

            return [
                {
                    "LogID": log.LogID,
                    "Username": log.Username or "N/A",
                    "Action": log.Action,
                    "Details": log.Details or "",
                    "Timestamp": log.Timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.Timestamp else "",
                    "IPAddress": log.IPAddress or "127.0.0.1"
                }
                for log in logs
            ]
