from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.database.schema import User, Role
from app.repositories.base_repository import BaseRepository
from app.config import MAX_FAILED_LOGIN_ATTEMPTS


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_username(self, username: str) -> Optional[User]:
        return (
            self.session.query(User)
            .options(joinedload(User.role))
            .filter(User.Username == username)
            .first()
        )

    def get_all_with_roles(self) -> List[User]:
        return (
            self.session.query(User)
            .options(joinedload(User.role))
            .order_by(User.UserID.asc())
            .all()
        )

    def increment_failed_attempts(self, user: User) -> bool:
        """Increment failed attempts and lock user if threshold reached. Returns True if locked."""
        user.FailedAttempts += 1
        if user.FailedAttempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.IsLocked = True
        self.session.flush()
        return user.IsLocked

    def reset_failed_attempts(self, user: User) -> None:
        user.FailedAttempts = 0
        self.session.flush()

    def update_last_login(self, user: User) -> None:
        user.LastLogin = datetime.utcnow()
        user.FailedAttempts = 0
        self.session.flush()

    def get_roles(self) -> List[Role]:
        return self.session.query(Role).all()

    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        return self.session.query(Role).filter(Role.RoleName == role_name).first()
