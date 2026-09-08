from datetime import date
from typing import Tuple, Optional, Dict, Any


class TransactionValidator:
    """Validator for Amdan (Receipt) & Akrajat (Payment) Transactions."""

    VALID_TYPES = ("RECEIPT", "PAYMENT", "AMDAN", "AKRAJAT")
    VALID_METHODS = ("Cash", "Bank", "Cheque", "Online Transfer", "Other")

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        # 1. Transaction Type
        txn_type = str(data.get("TransactionType", "")).strip().upper()
        if txn_type not in cls.VALID_TYPES:
            return False, f"Invalid Transaction Type '{txn_type}'. Must be 'RECEIPT' (Amdan) or 'PAYMENT' (Akrajat)."

        # 2. Account ID
        account_id = str(data.get("AccountID", "")).strip()
        if not account_id:
            return False, "Account selection is mandatory."

        # 3. Transaction Date
        txn_date = data.get("TransactionDate")
        if not txn_date or not isinstance(txn_date, (date,)):
            return False, "Valid transaction date is required."

        # 4. Amount
        try:
            amount = float(data.get("Amount", 0.0) or 0.0)
        except (ValueError, TypeError):
            return False, "Amount must be a valid numeric value."

        if amount <= 0.0:
            return False, "Transaction amount must be strictly greater than zero (Rs. 0.00)."

        if amount > 100_000_000.0:
            return False, "Transaction amount exceeds the maximum allowable limit (Rs. 100 Million)."

        # 5. Description / Narration
        description = str(data.get("Description", "")).strip()
        if not description:
            return False, "Transaction narration / description is mandatory."

        if len(description) > 255:
            return False, "Description must not exceed 255 characters."

        # 6. Payment Method
        method = str(data.get("PaymentMethod", "Cash")).strip()
        if not method:
            return False, "Payment method is required."

        return True, None
