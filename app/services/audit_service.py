from typing import List, Dict, Any, Optional
from sqlalchemy import or_
from app.database.connection import get_db_session
from app.database.schema import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    """Service layer for fetching read-only Audit Trail logs."""

    @staticmethod
    def get_audit_logs(
        query_str: Optional[str] = None,
        action_filter: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            q = session.query(AuditLog)

            if action_filter and action_filter != "ALL":
                q = q.filter(AuditLog.Action.ilike(f"%{action_filter}%"))

            if query_str and query_str.strip():
                term = f"%{query_str.strip()}%"
                q = q.filter(
                    or_(
                        AuditLog.Username.ilike(term),
                        AuditLog.Action.ilike(term),
                        AuditLog.Details.ilike(term)
                    )
                )

            logs = q.order_by(AuditLog.Timestamp.desc()).limit(limit).all()

            return [
                {
                    "LogID": log.LogID,
                    "Timestamp": log.Timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.Timestamp else "",
                    "Username": log.Username or "System",
                    "Action": log.Action or "",
                    "Details": log.Details or "",
                    "IPAddress": log.IPAddress or "127.0.0.1"
                }
                for log in logs
            ]
