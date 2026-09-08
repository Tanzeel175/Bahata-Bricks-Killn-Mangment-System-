from datetime import date, datetime
from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.database.schema import AccountType, LabourAccount, MoneyTransaction
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.labour_repository import LabourRepository
from app.repositories.audit_repository import AuditRepository
from app.validators.transaction_validator import TransactionValidator
from app.security.rbac import can_delete_records
from app.security.session import current_session


class MoneyTransactionService:
    """
    Unified Service Engine for Receipt (Amdan) & Payment (Akrajat) Financial Management.
    Handles atomic SQL transactions, cash-in-hand safety checks, role permissions,
    and automatic ledger synchronization across all account categories.
    """

    DEFAULT_SUGGESTED_NARRATIONS = {
        "RECEIPT": [
            "Advance deposit for brick purchase",
            "Cash payment received against sales bill",
            "Debt / Advance repayment from labourer",
            "Partial balance recovery",
            "Received security deposit",
            "Cash deposit by owner / partner",
            "Refund / rebate received from supplier",
            "Miscellaneous income"
        ],
        "PAYMENT": [
            "Weekly cash advance against piece-rate work",
            "Emergency medical advance to worker",
            "Settlement payment for production batch",
            "Customer refund for cancelled / adjusted order",
            "Payment to purchase party for raw material / coal",
            "Transporter freight charges",
            "Kiln maintenance & machinery expense",
            "Diesel / fuel expense payment",
            "Office tea & food expenses",
            "Owner withdrawal / personal drawing"
        ]
    }

    @classmethod
    def get_suggested_narrations(cls, txn_type: str) -> List[str]:
        t_key = "RECEIPT" if (txn_type or "").upper() in ("RECEIPT", "AMDAN") else "PAYMENT"
        return cls.DEFAULT_SUGGESTED_NARRATIONS.get(t_key, [])

    @staticmethod
    def get_next_transaction_no(txn_type: str) -> str:
        with get_db_session() as session:
            repo = TransactionRepository(session)
            return repo.get_next_transaction_no(txn_type)

    @staticmethod
    def get_categories() -> List[Dict[str, Any]]:
        """Load all account types from AccountTypes table."""
        with get_db_session() as session:
            types = session.query(AccountType).order_by(AccountType.AccountTypeName.asc()).all()
            return [
                {
                    "AccountTypeID": t.AccountTypeID,
                    "AccountTypeName": t.AccountTypeName,
                    "IsSystemDefined": t.IsSystemDefined
                }
                for t in types
            ]

    @staticmethod
    def get_accounts_by_category(category_id: int, include_omitted: bool = False) -> List[Dict[str, Any]]:
        """Load accounts belonging to a specific category."""
        with get_db_session() as session:
            labour_repo = LabourRepository(session)
            accounts = labour_repo.search_accounts(account_type_id=category_id, show_omitted=include_omitted)
            return [
                {
                    "WorkerID": a.WorkerID,
                    "EnglishName": a.EnglishName,
                    "UrduName": a.UrduName or "",
                    "CNIC": a.CNIC or "",
                    "Mobile": a.Mobile or "",
                    "Address": a.Address or "",
                    "IsOmitted": a.IsOmitted
                }
                for a in accounts
            ]

    @staticmethod
    def get_cash_summary(as_of_date: Optional[date] = None) -> Dict[str, float]:
        """Fetch current real-time cash, bank, and net totals."""
        with get_db_session() as session:
            repo = TransactionRepository(session)
            return repo.get_cash_summary(as_of_date)

    @staticmethod
    def save_transaction(
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
        allow_negative_cash: bool = False
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Record an Amdan (Receipt) or Akrajat (Payment) transaction atomically.
        Performs validation, cash-in-hand checks, audit logging, and commits.
        """
        norm_type = "RECEIPT" if (txn_type or "").upper() in ("RECEIPT", "AMDAN") else "PAYMENT"
        
        val_data = {
            "TransactionType": norm_type,
            "AccountID": account_id,
            "TransactionDate": txn_date,
            "Amount": amount,
            "Description": description,
            "PaymentMethod": payment_method
        }
        is_valid, err = TransactionValidator.validate(val_data)
        if not is_valid:
            return False, err or "Validation failed.", None

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                labour_repo = LabourRepository(session)
                account = labour_repo.get_by_worker_id(account_id)
                if not account:
                    return False, f"Account '{account_id}' does not exist.", None

                if account.IsOmitted and not current_session.is_admin:
                    return False, f"Account '{account.EnglishName}' is omitted/deactivated. Only Administrator can record transactions for omitted accounts.", None

                repo = TransactionRepository(session)
                audit_repo = AuditRepository(session)

                # Cash in hand guard for payments (Akrajat)
                if norm_type == "PAYMENT" and payment_method == "Cash":
                    cash_summary = repo.get_cash_summary()
                    current_cash = cash_summary.get("net_cash", 0.0)
                    if current_cash < amount:
                        if not current_session.is_admin:
                            return False, (
                                f"Insufficient Cash in Hand! Current balance is Rs. {current_cash:,.2f}, "
                                f"which is less than the requested payment amount of Rs. {amount:,.2f}. "
                                f"Munshi is not allowed to overdraw cash balance."
                            ), None
                        elif not allow_negative_cash:
                            return False, (
                                f"Cash Overdraw Warning: Current Cash-in-Hand is Rs. {current_cash:,.2f}. "
                                f"Processing Rs. {amount:,.2f} will leave cash negative (Rs. {current_cash - amount:,.2f}). "
                                f"Please confirm negative cash authorization to proceed."
                            ), None

                txn_no = repo.get_next_transaction_no(norm_type)

                txn = repo.create_transaction(
                    txn_no=txn_no,
                    txn_type=norm_type,
                    txn_date=txn_date,
                    account_id=account_id,
                    amount=amount,
                    description=description,
                    payment_method=payment_method,
                    bank_account=bank_account,
                    cheque_number=cheque_number,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    user_name=user_name
                )

                action_name = "TRANSACTION_RECEIPT_CREATE" if norm_type == "RECEIPT" else "TRANSACTION_PAYMENT_CREATE"
                type_label = "Amdan (Receipt)" if norm_type == "RECEIPT" else "Akrajat (Payment)"

                audit_repo.log_event(
                    action=action_name,
                    username=user_name,
                    user_id=current_session.user_id,
                    details=(
                        f"{action_name}: No={txn_no}, Type={norm_type}, Account={account_id} ({account.EnglishName}), "
                        f"Amount=Rs. {amount:,.2f}, Method={payment_method}"
                    )
                )

                session.commit()

                res_dict = {
                    "TransactionID": txn.TransactionID,
                    "TransactionNo": txn.TransactionNo,
                    "TransactionType": txn.TransactionType,
                    "TransactionDate": txn.TransactionDate,
                    "AccountID": txn.AccountID,
                    "AccountName": account.EnglishName,
                    "Amount": txn.Amount,
                    "PaymentMethod": txn.PaymentMethod,
                    "Description": txn.Description
                }

                msg = f"{type_label} '{txn_no}' of Rs. {amount:,.2f} successfully recorded for {account.EnglishName}."
                return True, msg, res_dict

        except Exception as e:
            return False, f"Failed to record money transaction: {e}", None

    @staticmethod
    def update_transaction(
        transaction_id: int,
        txn_date: date,
        account_id: str,
        amount: float,
        description: str,
        payment_method: str = "Cash",
        bank_account: Optional[str] = None,
        cheque_number: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Update an existing transaction. Only permitted for Administrators."""
        if not current_session.is_admin:
            return False, "Access Denied: Only Administrator has permission to edit financial transactions."

        val_data = {
            "TransactionType": "RECEIPT",  # validated type is not changing
            "AccountID": account_id,
            "TransactionDate": txn_date,
            "Amount": amount,
            "Description": description,
            "PaymentMethod": payment_method
        }
        is_valid, err = TransactionValidator.validate(val_data)
        if not is_valid:
            return False, err or "Validation failed."

        user_name = current_session.username or "Admin"

        try:
            with get_db_session() as session:
                repo = TransactionRepository(session)
                audit_repo = AuditRepository(session)

                txn = repo.get_by_id(transaction_id)
                if not txn or txn.IsDeleted:
                    return False, "Transaction not found or has been deleted."

                old_amt = txn.Amount
                old_desc = txn.Description

                repo.update_transaction(
                    transaction_id=transaction_id,
                    txn_date=txn_date,
                    account_id=account_id,
                    amount=amount,
                    description=description,
                    payment_method=payment_method,
                    bank_account=bank_account,
                    cheque_number=cheque_number,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    user_name=user_name
                )

                audit_repo.log_event(
                    action="TRANSACTION_UPDATE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"TRANSACTION_UPDATE: No={txn.TransactionNo}, OldAmount=Rs. {old_amt:,.2f}, NewAmount=Rs. {amount:,.2f}"
                )

                session.commit()
                return True, f"Transaction '{txn.TransactionNo}' successfully updated."
        except Exception as e:
            return False, f"Failed to update transaction: {e}"

    @staticmethod
    def delete_transaction(transaction_id: int, reason: str = "") -> Tuple[bool, str]:
        """Soft delete a transaction and reverse its effect. Only permitted for Administrators."""
        if not can_delete_records():
            return False, "Access Denied: Munshi cannot delete finalized financial transactions. Please contact Administrator."

        user_name = current_session.username or "Admin"

        try:
            with get_db_session() as session:
                repo = TransactionRepository(session)
                audit_repo = AuditRepository(session)

                txn = repo.get_by_id(transaction_id)
                if not txn or txn.IsDeleted:
                    return False, "Transaction not found or already deleted."

                txn_no = txn.TransactionNo
                amt = txn.Amount
                t_type = txn.TransactionType

                repo.soft_delete_transaction(transaction_id, user_name=user_name)

                audit_repo.log_event(
                    action="TRANSACTION_DELETE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"TRANSACTION_DELETE: Reversed No={txn_no}, Type={t_type}, Amount=Rs. {amt:,.2f}. Reason: {reason}"
                )

                session.commit()
                return True, f"Transaction '{txn_no}' has been safely deleted and its ledger effect reversed."
        except Exception as e:
            return False, f"Failed to delete transaction: {e}"

    @staticmethod
    def get_transactions(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        txn_type: Optional[str] = None,
        category_id: Optional[int] = None,
        account_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query register of transactions formatted for UI view."""
        with get_db_session() as session:
            repo = TransactionRepository(session)
            txns = repo.get_transactions(
                start_date=start_date,
                end_date=end_date,
                txn_type=txn_type,
                category_id=category_id,
                account_id=account_id,
                payment_method=payment_method,
                search_query=search_query,
                include_deleted=False
            )

            results = []
            for t in txns:
                acc_name = t.account.EnglishName if t.account else t.AccountID
                cat_name = t.account.account_type.AccountTypeName if t.account and t.account.account_type else "General"
                results.append({
                    "TransactionID": t.TransactionID,
                    "TransactionNo": t.TransactionNo,
                    "TransactionType": t.TransactionType,
                    "TransactionDate": t.TransactionDate,
                    "DateStr": t.TransactionDate.strftime("%d-%b-%Y") if t.TransactionDate else "",
                    "AccountID": t.AccountID,
                    "AccountName": acc_name,
                    "UrduName": t.account.UrduName if t.account else "",
                    "CategoryName": cat_name,
                    "Amount": t.Amount,
                    "PaymentMethod": t.PaymentMethod,
                    "BankAccount": t.BankAccount or "",
                    "ChequeNumber": t.ChequeNumber or "",
                    "Description": t.Description,
                    "ReferenceType": t.ReferenceType or "",
                    "ReferenceID": t.ReferenceID or "",
                    "CreatedBy": t.CreatedBy or "",
                    "CreatedDate": t.CreatedDate.strftime("%d-%b-%Y %H:%M") if t.CreatedDate else ""
                })
            return results

    @staticmethod
    def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single transaction details with account and category for printing / voucher generation."""
        with get_db_session() as session:
            repo = TransactionRepository(session)
            txn = repo.get_by_id(transaction_id)
            if not txn or txn.IsDeleted:
                return None

            account = txn.account
            acc_name = account.EnglishName if account else txn.AccountID
            urdu_name = account.UrduName if account else ""
            cat_name = account.account_type.AccountTypeName if account and account.account_type else "General"

            return {
                "TransactionID": txn.TransactionID,
                "TransactionNo": txn.TransactionNo,
                "TransactionType": txn.TransactionType,
                "TransactionDate": txn.TransactionDate,
                "DateStr": txn.TransactionDate.strftime("%d-%b-%Y") if txn.TransactionDate else "",
                "AccountID": txn.AccountID,
                "AccountName": acc_name,
                "UrduName": urdu_name,
                "CNIC": account.CNIC if account else "",
                "Mobile": account.Mobile if account else "",
                "Address": account.Address if account else "",
                "CategoryName": cat_name,
                "Amount": txn.Amount,
                "PaymentMethod": txn.PaymentMethod,
                "BankAccount": txn.BankAccount or "",
                "ChequeNumber": txn.ChequeNumber or "",
                "Description": txn.Description,
                "ReferenceType": txn.ReferenceType or "",
                "ReferenceID": txn.ReferenceID or "",
                "CreatedBy": txn.CreatedBy or "",
                "CreatedDate": txn.CreatedDate.strftime("%d-%b-%Y %H:%M") if txn.CreatedDate else ""
            }
