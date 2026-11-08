from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
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
        
        # Query all existing TransactionNo with this prefix to find the true max numeric sequence
        txns = (
            self.session.query(MoneyTransaction.TransactionNo)
            .filter(MoneyTransaction.TransactionNo.like(f"{prefix}-%"))
            .all()
        )

        max_seq = 0
        for (t_no,) in txns:
            if t_no:
                try:
                    parts = t_no.split("-")
                    if len(parts) == 2 and parts[1].isdigit():
                        num = int(parts[1])
                        if num > max_seq:
                            max_seq = num
                except Exception:
                    pass

        seq = max_seq + 1
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
        include_deleted: bool = False,
        limit: Optional[int] = None
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

        q = q.order_by(MoneyTransaction.TransactionDate.desc(), MoneyTransaction.TransactionID.desc())
        if limit and limit > 0:
            q = q.limit(limit)
        return q.all()

    def get_by_id_or_no(self, identifier: str, preferred_type: Optional[str] = None) -> Optional[MoneyTransaction]:
        """
        Lookup a transaction by TransactionNo (e.g. RCT-000005, PAY-000005, or entry number '5'),
        or fallback to internal TransactionID.
        If a pure number (e.g. '5') is entered:
        1. Check TransactionNo formatted with preferred_type prefix (e.g. 'RCT-000005' or 'PAY-000005')
        2. Check the other type prefix (e.g. 'PAY-000005' or 'RCT-000005')
        3. Check exact TransactionID
        """
        if not identifier:
            return None
        cleaned = identifier.strip().upper()
        q = (
            self.session.query(MoneyTransaction)
            .join(LabourAccount, MoneyTransaction.AccountID == LabourAccount.WorkerID)
            .options(joinedload(MoneyTransaction.account).joinedload(LabourAccount.account_type))
            .filter(MoneyTransaction.IsDeleted == False)
        )

        # 1. Exact match on TransactionNo (case-insensitive)
        txn = q.filter(func.upper(MoneyTransaction.TransactionNo) == cleaned).first()
        if txn:
            return txn

        # 2. Check if user typed variations like "RCT-5", "PAY-5", "RCT5", "PAY 5"
        import re
        m = re.match(r"^(RCT|PAY)[\s\-_]*(\d+)$", cleaned, re.IGNORECASE)
        if m:
            prefix = m.group(1).upper()
            num = int(m.group(2))
            formatted_no = f"{prefix}-{num:06d}"
            txn = q.filter(MoneyTransaction.TransactionNo == formatted_no).first()
            if txn:
                return txn

        # 3. If cleaned is pure digits (e.g. "5"):
        # Users consider this Entry #5, which corresponds to TransactionNo suffix 000005!
        if cleaned.isdigit():
            num = int(cleaned)
            formatted_suffix = f"{num:06d}"

            # If preferred_type is given ("RECEIPT" or "PAYMENT"), try that prefix first
            if preferred_type:
                pref_prefix = "RCT" if preferred_type.upper() == "RECEIPT" else "PAY"
                txn = q.filter(MoneyTransaction.TransactionNo == f"{pref_prefix}-{formatted_suffix}").first()
                if txn:
                    return txn
                # Try the other prefix
                alt_prefix = "PAY" if pref_prefix == "RCT" else "RCT"
                txn = q.filter(MoneyTransaction.TransactionNo == f"{alt_prefix}-{formatted_suffix}").first()
                if txn:
                    return txn
            else:
                # No preference: try RCT first, then PAY
                txn = q.filter(MoneyTransaction.TransactionNo == f"RCT-{formatted_suffix}").first()
                if txn:
                    return txn
                txn = q.filter(MoneyTransaction.TransactionNo == f"PAY-{formatted_suffix}").first()
                if txn:
                    return txn

            # Check if any TransactionNo ends with this number
            txn = q.filter(MoneyTransaction.TransactionNo.like(f"%-{formatted_suffix}")).first()
            if txn:
                return txn

            # Finally, fall back to internal TransactionID
            txn = q.filter(MoneyTransaction.TransactionID == num).first()
            if txn:
                return txn

        # 4. Partial substring match on TransactionNo
        return q.filter(MoneyTransaction.TransactionNo.ilike(f"%{cleaned}%")).first()

    def get_adjacent_transaction_id(self, current_id: Optional[int], direction: str = "prev") -> Optional[int]:
        """
        Get the ID of the adjacent non-deleted transaction.
        direction="prev": highest TransactionID < current_id (or latest overall if current_id is None)
        direction="next": lowest TransactionID > current_id
        """
        q = self.session.query(MoneyTransaction.TransactionID).filter(MoneyTransaction.IsDeleted == False)
        if direction == "prev":
            if current_id is not None:
                q = q.filter(MoneyTransaction.TransactionID < current_id)
            row = q.order_by(MoneyTransaction.TransactionID.desc()).first()
            return row[0] if row else None
        else:
            if current_id is None:
                return None
            row = q.filter(MoneyTransaction.TransactionID > current_id).order_by(MoneyTransaction.TransactionID.asc()).first()
            return row[0] if row else None


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
        description: Optional[str] = "",
        payment_method: str = "Cash",
        bank_account: Optional[str] = None,
        cheque_number: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        user_name: str = "System"
    ) -> MoneyTransaction:
        now = datetime.now(timezone.utc)
        for _attempt in range(3):
            txn = MoneyTransaction(
                TransactionNo=txn_no,
                TransactionType=txn_type.upper(),
                TransactionDate=txn_date,
                AccountID=account_id,
                Amount=amount,
                Description=(description or "").strip(),
                PaymentMethod=payment_method,
                BankAccount=bank_account,
                ChequeNumber=cheque_number,
                ReferenceType=reference_type,
                ReferenceID=reference_id,
                CreatedBy=user_name,
                CreatedDate=now,
                ModifiedDate=now,
                IsDeleted=False
            )
            try:
                self.session.add(txn)
                self.session.flush()
                return txn
            except IntegrityError:
                self.session.rollback()
                txn_no = self.get_next_transaction_no(txn_type)
        raise RuntimeError(f"Failed to generate unique transaction number after 3 retries.")

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
        txn.Description = (description or "").strip()
        txn.PaymentMethod = payment_method
        txn.BankAccount = bank_account
        txn.ChequeNumber = cheque_number
        txn.ReferenceType = reference_type
        txn.ReferenceID = reference_id
        txn.ModifiedBy = user_name
        txn.ModifiedDate = datetime.now(timezone.utc)
        self.session.flush()
        return txn

    def soft_delete_transaction(self, transaction_id: int, user_name: str = "System") -> bool:
        txn = self.get_by_id(transaction_id)
        if not txn:
            return False

        txn.IsDeleted = True
        txn.ModifiedBy = user_name
        txn.ModifiedDate = datetime.now(timezone.utc)
        self.session.flush()
        return True
