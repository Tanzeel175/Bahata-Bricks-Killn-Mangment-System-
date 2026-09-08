from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.database.schema import MoneyTransaction, LabourAccount, AccountType
from app.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[MoneyTransaction]):
    """
    Data Access Layer for unified MoneyTransactions (Amdan / Receipts & Akrajat / Payments).
    Supports multi-criteria querying, transaction numbering, cash aggregation, and soft deletes.
    """

    def __init__(self, session: Session):
        super().__init__(session, MoneyTransaction)

    def get_next_transaction_no(self, txn_type: str) -> str:
        """
        Generate sequential unique transaction number.
        RECEIPT -> RCT-000001, RCT-000002...
        PAYMENT -> PAY-000001, PAY-000002...
        """
        prefix = "RCT" if (txn_type or "").upper() in ("RECEIPT", "AMDAN") else "PAY"
        
        # Query highest ID for this prefix
        last_txn = (
            self.session.query(MoneyTransaction)
            .filter(MoneyTransaction.TransactionNo.like(f"{prefix}-%"))
            .order_by(MoneyTransaction.TransactionID.desc())
            .first()
        )

        seq = 1
        if last_txn and last_txn.TransactionNo:
            try:
                parts = last_txn.TransactionNo.split("-")
                if len(parts) == 2 and parts[1].isdigit():
                    seq = int(parts[1]) + 1
            except Exception:
                seq = (last_txn.TransactionID or 0) + 1
        else:
            # Fallback to total count + 1
            cnt = self.session.query(MoneyTransaction).filter(MoneyTransaction.TransactionType == txn_type).count()
            seq = cnt + 1

        return f"{prefix}-{seq:06d}"

    def get_by_account(
        self,
        account_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_deleted: bool = False
    ) -> List[MoneyTransaction]:
        """Fetch all transactions for an account sorted chronologically."""
        q = self.session.query(MoneyTransaction).filter(MoneyTransaction.AccountID == account_id)
        if not include_deleted:
            q = q.filter(MoneyTransaction.IsDeleted == False)
        if start_date:
            q = q.filter(MoneyTransaction.TransactionDate >= start_date)
        if end_date:
            q = q.filter(MoneyTransaction.TransactionDate <= end_date)

        return q.order_by(MoneyTransaction.TransactionDate.asc(), MoneyTransaction.TransactionID.asc()).all()

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        txn_type: Optional[str] = None,
        category_id: Optional[int] = None,
        account_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        search_query: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[MoneyTransaction]:
        """Search and filter transactions with eager loaded account details."""
        q = (
            self.session.query(MoneyTransaction)
            .join(LabourAccount, MoneyTransaction.AccountID == LabourAccount.WorkerID)
            .options(joinedload(MoneyTransaction.account).joinedload(LabourAccount.account_type))
        )

        if not include_deleted:
            q = q.filter(MoneyTransaction.IsDeleted == False)

        if start_date:
            q = q.filter(MoneyTransaction.TransactionDate >= start_date)
        if end_date:
            q = q.filter(MoneyTransaction.TransactionDate <= end_date)
        if txn_type and txn_type.upper() in ("RECEIPT", "PAYMENT"):
            q = q.filter(MoneyTransaction.TransactionType == txn_type.upper())
        if category_id:
            q = q.filter(LabourAccount.AccountTypeID == category_id)
        if account_id:
            q = q.filter(MoneyTransaction.AccountID == account_id)
        if payment_method and payment_method != "All":
            q = q.filter(MoneyTransaction.PaymentMethod == payment_method)
        if search_query:
            term = f"%{search_query.strip()}%"
            q = q.filter(
                or_(
                    MoneyTransaction.TransactionNo.like(term),
                    MoneyTransaction.Description.like(term),
                    MoneyTransaction.ReferenceType.like(term),
                    MoneyTransaction.ReferenceID.like(term),
                    LabourAccount.EnglishName.like(term),
                    LabourAccount.UrduName.like(term)
                )
            )

        return q.order_by(MoneyTransaction.TransactionDate.desc(), MoneyTransaction.TransactionID.desc()).all()

    def get_cash_summary(self, as_of_date: Optional[date] = None) -> Dict[str, float]:
        """
        Calculate total cash receipts (Amdan), total cash payments (Akrajat), and current net cash.
        Also calculates total bank and overall movement.
        """
        base_q = self.session.query(MoneyTransaction).filter(MoneyTransaction.IsDeleted == False)
        if as_of_date:
            base_q = base_q.filter(MoneyTransaction.TransactionDate <= as_of_date)

        # Cash Amdan
        cash_amdan = (
            base_q.filter(
                MoneyTransaction.TransactionType == "RECEIPT",
                MoneyTransaction.PaymentMethod == "Cash"
            ).with_entities(func.coalesce(func.sum(MoneyTransaction.Amount), 0.0)).scalar()
        ) or 0.0

        # Cash Akrajat
        cash_akrajat = (
            base_q.filter(
                MoneyTransaction.TransactionType == "PAYMENT",
                MoneyTransaction.PaymentMethod == "Cash"
            ).with_entities(func.coalesce(func.sum(MoneyTransaction.Amount), 0.0)).scalar()
        ) or 0.0

        # Bank Receipts & Payments
        bank_amdan = (
            base_q.filter(
                MoneyTransaction.TransactionType == "RECEIPT",
                MoneyTransaction.PaymentMethod != "Cash"
            ).with_entities(func.coalesce(func.sum(MoneyTransaction.Amount), 0.0)).scalar()
        ) or 0.0

        bank_akrajat = (
            base_q.filter(
                MoneyTransaction.TransactionType == "PAYMENT",
                MoneyTransaction.PaymentMethod != "Cash"
            ).with_entities(func.coalesce(func.sum(MoneyTransaction.Amount), 0.0)).scalar()
        ) or 0.0

        # Total Amdan & Akrajat across all methods
        total_amdan = cash_amdan + bank_amdan
        total_akrajat = cash_akrajat + bank_akrajat
        net_cash = cash_amdan - cash_akrajat

        return {
            "cash_amdan": float(cash_amdan),
            "cash_akrajat": float(cash_akrajat),
            "net_cash": float(net_cash),
            "bank_amdan": float(bank_amdan),
            "bank_akrajat": float(bank_akrajat),
            "net_bank": float(bank_amdan - bank_akrajat),
            "total_amdan": float(total_amdan),
            "total_akrajat": float(total_akrajat),
            "net_total": float(total_amdan - total_akrajat)
        }

    def create_transaction(
        self,
        txn_no: str,
        txn_type: str,
        txn_date: date,
        account_id: str,
        amount: float,
        description: str,
        payment_method: str = "Cash",
        bank_account: Optional[str] = None,
        cheque_number: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        user_name: str = "System"
    ) -> MoneyTransaction:
        txn = MoneyTransaction(
            TransactionNo=txn_no,
            TransactionType=txn_type.upper(),
            TransactionDate=txn_date,
            AccountID=account_id,
            Amount=amount,
            Description=description,
            PaymentMethod=payment_method,
            BankAccount=bank_account,
            ChequeNumber=cheque_number,
            ReferenceType=reference_type,
            ReferenceID=reference_id,
            CreatedBy=user_name,
            CreatedDate=datetime.utcnow(),
            ModifiedDate=datetime.utcnow(),
            IsDeleted=False
        )
        self.session.add(txn)
        self.session.flush()
        return txn

    def update_transaction(
        self,
        transaction_id: int,
        txn_date: date,
        account_id: str,
        amount: float,
        description: str,
        payment_method: str = "Cash",
        bank_account: Optional[str] = None,
        cheque_number: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        user_name: str = "System"
    ) -> Optional[MoneyTransaction]:
        txn = self.get_by_id(transaction_id)
        if not txn:
            return None

        txn.TransactionDate = txn_date
        txn.AccountID = account_id
        txn.Amount = amount
        txn.Description = description
        txn.PaymentMethod = payment_method
        txn.BankAccount = bank_account
        txn.ChequeNumber = cheque_number
        txn.ReferenceType = reference_type
        txn.ReferenceID = reference_id
        txn.ModifiedBy = user_name
        txn.ModifiedDate = datetime.utcnow()
        self.session.flush()
        return txn

    def soft_delete_transaction(self, transaction_id: int, user_name: str = "System") -> bool:
        txn = self.get_by_id(transaction_id)
        if not txn:
            return False

        txn.IsDeleted = True
        txn.ModifiedBy = user_name
        txn.ModifiedDate = datetime.utcnow()
        self.session.flush()
        return True
