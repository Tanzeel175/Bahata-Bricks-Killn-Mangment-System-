from functools import wraps
from app.security.session import current_session


class PermissionError(Exception):
    """Raised when an unprivileged user attempts an authorized action."""
    pass


def require_role(*allowed_roles: str):
    """Decorator to enforce role permissions on service methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_session.is_authenticated:
                raise PermissionError("User is not authenticated.")
            if current_session.role_name not in allowed_roles:
                raise PermissionError(
                    f"Access Denied: Action requires one of {allowed_roles} roles. "
                    f"Current role: '{current_session.role_name}'."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func):
    """Decorator requiring Administrator role."""
    return require_role("Administrator")(func)


def can_delete_records() -> bool:
    """Munshi cannot delete data under any circumstances."""
    return current_session.is_admin


def can_manage_users() -> bool:
    """Munshi cannot create or manage user accounts."""
    return current_session.is_admin
