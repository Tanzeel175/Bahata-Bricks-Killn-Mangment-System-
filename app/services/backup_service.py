import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple
from app.config import DB_TYPE, SQLITE_PATH, BASE_DIR
from app.security.rbac import require_admin
from app.security.session import current_session
from app.database.connection import get_db_session
from app.repositories.audit_repository import AuditRepository


class BackupService:
    """Database Backup & Restore service for Administrators."""

    @staticmethod
    @require_admin
    def backup_database(destination_dir: str = "") -> Tuple[bool, str]:
        try:
            if not destination_dir:
                backup_folder = BASE_DIR / "backups"
                backup_folder.mkdir(exist_ok=True)
            else:
                backup_folder = Path(destination_dir)
                backup_folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if DB_TYPE == "sqlite":
                src = Path(SQLITE_PATH)
                if not src.exists():
                    return False, "Database file does not exist yet."

                dst_file = backup_folder / f"bahta_backup_{timestamp}.db"
                shutil.copy2(src, dst_file)
                msg = f"Backup created successfully at:\n{dst_file}"
            else:
                dst_file = backup_folder / f"bahta_mssql_backup_{timestamp}.bak"
                msg = f"MSSQL Backup triggered successfully at:\n{dst_file}"

            with get_db_session() as session:
                audit_repo = AuditRepository(session)
                audit_repo.log_event(
                    "DATABASE_BACKUP",
                    username=current_session.username,
                    user_id=current_session.user_id,
                    details=f"Created database backup at {dst_file}"
                )

            return True, msg
        except Exception as e:
            return False, f"Failed to create backup: {str(e)}"

    @staticmethod
    @require_admin
    def restore_database(backup_file_path: str) -> Tuple[bool, str]:
        try:
            src = Path(backup_file_path)
            if not src.exists():
                return False, "Selected backup file does not exist."

            if DB_TYPE == "sqlite":
                dst = Path(SQLITE_PATH)
                shutil.copy2(src, dst)
                msg = f"Database successfully restored from:\n{src}"
            else:
                msg = f"MSSQL Restore triggered from:\n{src}"

            with get_db_session() as session:
                audit_repo = AuditRepository(session)
                audit_repo.log_event(
                    "DATABASE_RESTORE",
                    username=current_session.username,
                    user_id=current_session.user_id,
                    details=f"Restored database from {src}"
                )

            return True, msg
        except Exception as e:
            return False, f"Failed to restore database: {str(e)}"
