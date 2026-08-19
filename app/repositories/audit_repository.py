from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.schema import AuditLog
from app.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session):
        super().__init__(session, AuditLog)

    def log_event(
        self,
        action: str,
        username: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = "127.0.0.1"
    ) -> AuditLog:
        entry = AuditLog(
            Action=action,
            Username=username,
            UserID=user_id,
            Details=details,
            IPAddress=ip_address
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def get_recent_logs(self, limit: int = 100) -> List[AuditLog]:
        return (
            self.session.query(AuditLog)
            .order_by(AuditLog.Timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_logs_by_user(self, username: str, limit: int = 50) -> List[AuditLog]:
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.Username == username)
            .order_by(AuditLog.Timestamp.desc())
            .limit(limit)
            .all()
        )
