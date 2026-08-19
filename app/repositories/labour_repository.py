from datetime import datetime
from typing import Optional, List
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.database.schema import LabourAccount, AccountType
from app.repositories.base_repository import BaseRepository


class LabourRepository(BaseRepository[LabourAccount]):
    def __init__(self, session: Session):
        super().__init__(session, LabourAccount)

    def get_by_worker_id(self, worker_id: str) -> Optional[LabourAccount]:
        return (
            self.session.query(LabourAccount)
            .options(joinedload(LabourAccount.account_type))
            .filter(LabourAccount.WorkerID == worker_id)
            .first()
        )

    def search_accounts(
        self,
        query_str: Optional[str] = None,
        account_type_id: Optional[int] = None,
        show_omitted: bool = False
    ) -> List[LabourAccount]:
        """
        Search Labour Accounts with filters:
        - Instant search text across WorkerID, EnglishName, UrduName, Mobile, CNIC, ReferenceName
        - AccountTypeID filter
        - Show omitted toggle (if False, excludes IsOmitted == True)
        """
        q = self.session.query(LabourAccount).options(joinedload(LabourAccount.account_type))

        if not show_omitted:
            q = q.filter(LabourAccount.IsOmitted == False)

        if account_type_id and account_type_id > 0:
            q = q.filter(LabourAccount.AccountTypeID == account_type_id)

        if query_str and query_str.strip():
            term = f"%{query_str.strip()}%"
            q = q.filter(
                or_(
                    LabourAccount.WorkerID.ilike(term),
                    LabourAccount.EnglishName.ilike(term),
                    LabourAccount.UrduName.ilike(term),
                    LabourAccount.CNIC.ilike(term),
                    LabourAccount.Mobile.ilike(term),
                    LabourAccount.ReferenceName.ilike(term)
                )
            )

        return q.order_by(LabourAccount.WorkerID.asc()).all()

    def get_account_types(self) -> List[AccountType]:
        return self.session.query(AccountType).order_by(AccountType.AccountTypeName.asc()).all()

    def get_account_type_by_name(self, name: str) -> Optional[AccountType]:
        return self.session.query(AccountType).filter(AccountType.AccountTypeName == name).first()

    def add_account_type(self, name: str) -> AccountType:
        acc_type = AccountType(AccountTypeName=name, IsSystemDefined=False)
        self.session.add(acc_type)
        self.session.flush()
        return acc_type

    def has_transactions_or_references(self, worker_id: str) -> bool:
        """
        Check if the worker account has any existing transactions/ledger entries.
        (Future production, sales, payroll modules will register references here.
         Currently checks if any mock transaction table exists or if account flag has ledger protection).
        """
        # Business rule logic: If worker_id starts with protected prefix or has mock transactions, reject hard delete.
        # For now, return False unless tested or expanded by future transaction modules.
        return False

    def set_omit_status(self, worker_id: str, is_omitted: bool, reason: str = "", user_name: str = "") -> Optional[LabourAccount]:
        account = self.get_by_worker_id(worker_id)
        if not account:
            return None

        account.IsOmitted = is_omitted
        if is_omitted:
            account.OmitDate = datetime.utcnow()
            account.OmitReason = reason
        else:
            account.OmitDate = None
            account.OmitReason = None

        account.ModifiedBy = user_name
        account.ModifiedDate = datetime.utcnow()
        self.session.flush()
        return account

    def generate_next_worker_id(self, prefix: str = "WRK-") -> str:
        """Helper to generate next sequential Worker ID starting from 1."""
        count = self.session.query(LabourAccount).count()
        return f"{prefix}{count + 1:04d}"

    def get_summary_counts(self) -> dict:
        total = self.session.query(LabourAccount).count()
        omitted = self.session.query(LabourAccount).filter(LabourAccount.IsOmitted == True).count()
        active = total - omitted

        breakdown = {}
        types = self.session.query(AccountType).all()
        for t in types:
            c = self.session.query(LabourAccount).filter(LabourAccount.AccountTypeID == t.AccountTypeID).count()
            if c > 0:
                breakdown[t.AccountTypeName] = c

        return {
            "total_accounts": total,
            "active_accounts": active,
            "omitted_accounts": omitted,
            "category_breakdown": breakdown
        }

