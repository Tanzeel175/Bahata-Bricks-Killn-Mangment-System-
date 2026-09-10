from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.database.schema import LabourAccount, AccountType
from app.repositories.labour_repository import LabourRepository
from app.repositories.audit_repository import AuditRepository
from app.security.rbac import can_delete_records, require_admin, require_authenticated
from app.security.session import current_session
from app.validators.labour_validator import (
    validate_labour_account, format_cnic, format_mobile
)


class LabourService:
    """Service layer for Labour / Account Master management."""

    @staticmethod
    def search_accounts(
        query_str: Optional[str] = None,
        account_type_id: Optional[int] = None,
        show_omitted: bool = False
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = LabourRepository(session)
            accounts = repo.search_accounts(query_str, account_type_id, show_omitted)
            return [
                {
                    "WorkerID": a.WorkerID,
                    "AccountTypeID": a.AccountTypeID,
                    "AccountTypeName": a.account_type.AccountTypeName if a.account_type else "",
                    "EnglishName": a.EnglishName,
                    "UrduName": a.UrduName or "",
                    "FatherName": a.FatherName or "",
                    "CNIC": a.CNIC,
                    "Mobile": a.Mobile,
                    "ReferenceName": a.ReferenceName,
                    "ReferenceMobile": a.ReferenceMobile,
                    "Address": a.Address or "",
                    "Email": a.Email or "",
                    "DailyModularTarget": a.DailyModularTarget,
                    "DailyFillerTarget": a.DailyFillerTarget,
                    "Remarks": a.Remarks or "",
                    "IsOmitted": a.IsOmitted,
                    "OmitDate": a.OmitDate.strftime("%Y-%m-%d %H:%M") if a.OmitDate else "",
                    "OmitReason": a.OmitReason or "",
                    "CreatedBy": a.CreatedBy or "",
                    "CreatedDate": a.CreatedDate.strftime("%Y-%m-%d") if a.CreatedDate else ""
                }
                for a in accounts
            ]

    @staticmethod
    def get_account_by_id(worker_id: str) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            repo = LabourRepository(session)
            account = repo.get_by_worker_id(worker_id)
            if not account:
                return None
            return {
                "WorkerID": account.WorkerID,
                "AccountTypeID": account.AccountTypeID,
                "AccountTypeName": account.account_type.AccountTypeName if account.account_type else "",
                "EnglishName": account.EnglishName,
                "UrduName": account.UrduName or "",
                "FatherName": account.FatherName or "",
                "CNIC": account.CNIC,
                "Mobile": account.Mobile,
                "ReferenceName": account.ReferenceName,
                "ReferenceMobile": account.ReferenceMobile,
                "Address": account.Address or "",
                "Email": account.Email or "",
                "DailyModularTarget": account.DailyModularTarget,
                "DailyFillerTarget": account.DailyFillerTarget,
                "Remarks": account.Remarks or "",
                "IsOmitted": account.IsOmitted,
                "OmitDate": account.OmitDate.strftime("%Y-%m-%d %H:%M") if account.OmitDate else "",
                "OmitReason": account.OmitReason or ""
            }

    @staticmethod
    @require_authenticated
    def save_account(data: Dict[str, Any], is_edit_mode: bool = False) -> Tuple[bool, str]:
        # Perform validation
        valid, errors = validate_labour_account(data)
        if not valid:
            return False, "\n".join(errors)

        worker_id = str(data["WorkerID"]).strip()
        account_type_id = int(data["AccountTypeID"])
        cnic_formatted = format_cnic(str(data["CNIC"]))
        mobile_formatted = format_mobile(str(data["Mobile"]))
        ref_mobile_formatted = format_mobile(str(data["ReferenceMobile"]))

        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)

            existing = repo.get_by_worker_id(worker_id)

            if not is_edit_mode:
                if existing:
                    return False, f"Worker ID '{worker_id}' already exists. Please specify a unique Worker ID."

                account = LabourAccount(
                    WorkerID=worker_id,
                    AccountTypeID=account_type_id,
                    EnglishName=str(data["EnglishName"]).strip(),
                    UrduName=str(data.get("UrduName", "")).strip() or None,
                    FatherName=str(data.get("FatherName", "")).strip() or None,
                    CNIC=cnic_formatted,
                    Mobile=mobile_formatted,
                    ReferenceName=str(data["ReferenceName"]).strip(),
                    ReferenceMobile=ref_mobile_formatted,
                    Address=str(data.get("Address", "")).strip() or None,
                    Email=str(data.get("Email", "")).strip() or None,
                    DailyModularTarget=float(data.get("DailyModularTarget", 0.0)),
                    DailyFillerTarget=float(data.get("DailyFillerTarget", 0.0)),
                    Remarks=str(data.get("Remarks", "")).strip() or None,
                    IsOmitted=False,
                    CreatedBy=current_session.username,
                    CreatedDate=datetime.utcnow(),
                    ModifiedBy=current_session.username,
                    ModifiedDate=datetime.utcnow()
                )
                repo.add(account)
                audit_repo.log_event(
                    "LABOUR_ACCOUNT_CREATED",
                    username=current_session.username,
                    user_id=current_session.user_id,
                    details=f"Created Labour Account WorkerID '{worker_id}' ({data['EnglishName']})"
                )
                return True, f"Labour Account '{worker_id}' saved successfully."

            else:
                if not existing:
                    return False, f"Labour Account '{worker_id}' does not exist."

                existing.AccountTypeID = account_type_id
                existing.EnglishName = str(data["EnglishName"]).strip()
                existing.UrduName = str(data.get("UrduName", "")).strip() or None
                existing.FatherName = str(data.get("FatherName", "")).strip() or None
                existing.CNIC = cnic_formatted
                existing.Mobile = mobile_formatted
                existing.ReferenceName = str(data["ReferenceName"]).strip()
                existing.ReferenceMobile = ref_mobile_formatted
                existing.Address = str(data.get("Address", "")).strip() or None
                existing.Email = str(data.get("Email", "")).strip() or None
                existing.DailyModularTarget = float(data.get("DailyModularTarget", 0.0))
                existing.DailyFillerTarget = float(data.get("DailyFillerTarget", 0.0))
                existing.Remarks = str(data.get("Remarks", "")).strip() or None
                existing.ModifiedBy = current_session.username
                existing.ModifiedDate = datetime.utcnow()

                repo.update(existing)
                audit_repo.log_event(
                    "LABOUR_ACCOUNT_UPDATED",
                    username=current_session.username,
                    user_id=current_session.user_id,
                    details=f"Updated Labour Account WorkerID '{worker_id}'"
                )
                return True, f"Labour Account '{worker_id}' updated successfully."

    @staticmethod
    @require_authenticated
    def omit_account(worker_id: str, reason: str) -> Tuple[bool, str]:
        if not reason or not reason.strip():
            return False, "Omit reason is required."

        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)

            acc = repo.set_omit_status(
                worker_id=worker_id,
                is_omitted=True,
                reason=reason.strip(),
                user_name=current_session.username or "SYSTEM"
            )
            if not acc:
                return False, "Account not found."

            audit_repo.log_event(
                "LABOUR_ACCOUNT_OMITTED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Omitted account '{worker_id}'. Reason: {reason}"
            )
            return True, f"Account '{worker_id}' has been omitted (deactivated)."

    @staticmethod
    @require_admin
    def reactivate_account(worker_id: str) -> Tuple[bool, str]:
        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)

            acc = repo.set_omit_status(
                worker_id=worker_id,
                is_omitted=False,
                reason="",
                user_name=current_session.username or "SYSTEM"
            )
            if not acc:
                return False, "Account not found."

            audit_repo.log_event(
                "LABOUR_ACCOUNT_REACTIVATED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Reactivated account '{worker_id}'"
            )
            return True, f"Account '{worker_id}' has been reactivated."

    @staticmethod
    @require_authenticated
    def delete_account(worker_id: str) -> Tuple[bool, str]:
        # Rule check: Munshi cannot delete
        if not can_delete_records():
            return False, "Access Denied: Munshi role is not permitted to delete accounts."

        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)

            account = repo.get_by_worker_id(worker_id)
            if not account:
                return False, "Account not found."

            # Check if ledger or transactions exist
            if repo.has_transactions_or_references(worker_id):
                return False, "This account contains historical transactions and cannot be deleted. Please use Omit instead."

            name = account.EnglishName
            repo.delete(account)

            audit_repo.log_event(
                "LABOUR_ACCOUNT_DELETED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Hard deleted account '{worker_id}' ({name})"
            )
            return True, f"Account '{worker_id}' deleted successfully."

    @staticmethod
    def get_account_types() -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = LabourRepository(session)
            types = repo.get_account_types()
            return [
                {
                    "AccountTypeID": t.AccountTypeID,
                    "AccountTypeName": t.AccountTypeName,
                    "IsSystemDefined": t.IsSystemDefined
                }
                for t in types
            ]

    @staticmethod
    @require_admin
    def create_account_type(name: str) -> Tuple[bool, str]:
        if not name or not name.strip():
            return False, "Account type name cannot be empty."

        name = name.strip()
        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)

            existing = repo.get_account_type_by_name(name)
            if existing:
                return False, f"Account type '{name}' already exists."

            repo.add_account_type(name)
            audit_repo.log_event(
                "ACCOUNT_TYPE_CREATED",
                username=current_session.username,
                user_id=current_session.user_id,
                details=f"Added custom Account Type '{name}'"
            )
            return True, f"Account type '{name}' added successfully."

    @staticmethod
    def generate_worker_id() -> str:
        with get_db_session() as session:
            repo = LabourRepository(session)
            return repo.generate_next_worker_id("W-")

    @staticmethod
    def get_dashboard_summary() -> Dict[str, Any]:
        with get_db_session() as session:
            repo = LabourRepository(session)
            audit_repo = AuditRepository(session)
            counts = repo.get_summary_counts()
            recent_logs = audit_repo.get_recent_logs(limit=10) if current_session.is_admin else []
            counts["recent_logs"] = [
                {
                    "Username": log.Username or "N/A",
                    "Action": log.Action,
                    "Details": log.Details or "",
                    "Timestamp": log.Timestamp.strftime("%H:%M:%S (%d-%b)") if log.Timestamp else ""
                }
                for log in recent_logs
            ]
            return counts
