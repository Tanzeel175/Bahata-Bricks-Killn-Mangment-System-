import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Tuple

from app.config import DB_TYPE, SQLITE_PATH, BASE_DIR
from app.security.rbac import require_admin
from app.security.session import current_session
from app.database.connection import get_db_session
from app.database.connection import get_engine
from app.repositories.audit_repository import AuditRepository


class BackupService:
    """Administrator-only, integrity-checked database backup and restore service."""

    REQUIRED_SQLITE_TABLES = {"Users", "Roles", "LabourAccounts", "AuditLogs"}

    @staticmethod
    def _protect_file(path: Path) -> None:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    @classmethod
    def _validate_sqlite_backup(cls, path: Path) -> Tuple[bool, str]:
        if not path.is_file() or path.stat().st_size == 0:
            return False, "Selected backup is missing or empty."
        try:
            conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity.lower() != "ok":
                    return False, "Selected backup failed the SQLite integrity check."
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if cls.REQUIRED_SQLITE_TABLES - tables:
                    return False, "Selected backup is not a Bahata ERP database."
            finally:
                conn.close()
        except (sqlite3.DatabaseError, OSError, ValueError):
            return False, "Selected backup is not a valid SQLite database."
        return True, ""

    @staticmethod
    def _sqlite_backup(source: Path, destination: Path) -> None:
        """Use SQLite's online backup API so WAL data is included consistently."""
        source_conn = sqlite3.connect(source)
        destination_conn = sqlite3.connect(destination)
        try:
            source_conn.backup(destination_conn)
        finally:
            destination_conn.close()
            source_conn.close()
        BackupService._protect_file(destination)

    @staticmethod
    @require_admin
    def backup_database(destination_dir: str = "") -> Tuple[bool, str]:
        try:
            backup_folder = Path(destination_dir) if destination_dir else BASE_DIR / "backups"
            backup_folder.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if DB_TYPE != "sqlite":
                return False, "MSSQL backup must be performed by the configured database server administrator."
            src = Path(SQLITE_PATH)
            if not src.exists():
                return False, "Database file does not exist yet."
            dst_file = backup_folder / f"bahata_backup_{timestamp}.db"
            BackupService._sqlite_backup(src, dst_file)
            with get_db_session() as session:
                AuditRepository(session).log_event(
                    "DATABASE_BACKUP", username=current_session.username, user_id=current_session.user_id,
                    details=f"Created database backup at {dst_file}"
                )
            return True, f"Integrity-consistent backup created at:\n{dst_file}"
        except Exception:
            return False, "Backup failed. Check that the destination is writable and try again."

    @staticmethod
    @require_admin
    def restore_database(backup_file_path: str) -> Tuple[bool, str]:
        try:
            src = Path(backup_file_path).resolve(strict=True)
            if DB_TYPE != "sqlite":
                return False, "MSSQL restore must be performed by the configured database server administrator."
            dst = Path(SQLITE_PATH).resolve()
            if src == dst:
                return False, "The selected file is already the active database."
            valid, reason = BackupService._validate_sqlite_backup(src)
            if not valid:
                return False, reason

            safety_folder = dst.parent / "restore-safety-copies"
            safety_folder.mkdir(parents=True, exist_ok=True)
            safety_copy = safety_folder / f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            if dst.exists():
                BackupService._sqlite_backup(dst, safety_copy)
            # Build and validate a separate SQLite file before replacing the live database.
            staging = dst.with_suffix(dst.suffix + ".restore-staging")
            try:
                if staging.exists():
                    staging.unlink()
                BackupService._sqlite_backup(src, staging)
                valid, reason = BackupService._validate_sqlite_backup(staging)
                if not valid:
                    return False, reason
                # Release any SQLite handles before replacing the database file.
                get_engine().dispose()
                os.replace(staging, dst)
                for sidecar in (dst.with_name(dst.name + "-wal"), dst.with_name(dst.name + "-shm")):
                    if sidecar.exists():
                        sidecar.unlink()
                BackupService._protect_file(dst)
            finally:
                if staging.exists():
                    staging.unlink()

            with get_db_session() as session:
                AuditRepository(session).log_event(
                    "DATABASE_RESTORE", username=current_session.username, user_id=current_session.user_id,
                    details=f"Restored validated backup from {src.name}; pre-restore copy: {safety_copy.name}"
                )
            return True, f"Database restored. A safety copy was saved at:\n{safety_copy}"
        except FileNotFoundError:
            return False, "Selected backup file does not exist."
        except Exception:
            return False, "Restore failed. Your active database was not replaced."
