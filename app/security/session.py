from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import SESSION_TIMEOUT_MINUTES


class UserSession:
    """Singleton session state manager for active logged in user."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSession, cls).__new__(cls)
            cls._instance._user_data = None
            cls._instance._last_activity = None
        return cls._instance

    def login(self, user_id: int, username: str, full_name: str, role_name: str):
        self._user_data = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "role_name": role_name,
            "login_time": datetime.now()
        }
        self.touch_activity()

    def logout(self):
        self._user_data = None
        self._last_activity = None

    def touch_activity(self):
        self._last_activity = datetime.now()

    @property
    def is_authenticated(self) -> bool:
        if self._user_data is None:
            return False
        if self.is_expired():
            self.logout()
            return False
        return True

    def is_expired(self) -> bool:
        if self._last_activity is None:
            return True
        elapsed = datetime.now() - self._last_activity
        return elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        if self.is_authenticated:
            return self._user_data
        return None

    @property
    def user_id(self) -> Optional[int]:
        return self._user_data.get("user_id") if self._user_data else None

    @property
    def username(self) -> Optional[str]:
        return self._user_data.get("username") if self._user_data else None

    @property
    def full_name(self) -> Optional[str]:
        return self._user_data.get("full_name") if self._user_data else None

    @property
    def role_name(self) -> Optional[str]:
        return self._user_data.get("role_name") if self._user_data else None

    @property
    def is_admin(self) -> bool:
        return self.role_name == "Administrator"

    @property
    def is_munshi(self) -> bool:
        return self.role_name == "Munshi"


current_session = UserSession()
