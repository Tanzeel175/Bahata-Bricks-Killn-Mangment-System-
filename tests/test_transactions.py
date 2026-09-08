import pytest
from datetime import date
from app.database.init_db import init_db
from app.database.connection import get_db_session
from app.database.schema import MoneyTransaction
from app.services.money_transaction_service import MoneyTransactionService
from app.services.ledger_service import LedgerService
from app.security.session import current_session


@pytest.fixture(autouse=True)
def setup_test_database():
    """Reset and seed fresh test database for each test case."""
    init_db()
    current_session.login(1, "admin", "System Administrator", "Administrator")
    yield
    current_session.logout()


def test_transaction_numbering():
    """Verify distinct sequential numbering for receipts and payments."""
    no_rcpt = MoneyTransactionService.get_next_transaction_no("RECEIPT")
    no_pay = MoneyTransactionService.get_next_transaction_no("PAYMENT")

    assert no_rcpt.startswith("RCT-")
    assert no_pay.startswith("PAY-")
    assert len(no_rcpt) == 10  # RCT-000001
    assert len(no_pay) == 10   # PAY-000001


def test_create_amdan_receipt_customer():
    """Verify customer Amdan (deposit) increases cash and credits customer khata."""
    # 1. Baseline cash
    init_cash = MoneyTransactionService.get_cash_summary()["net_cash"]

    # 2. Record Customer Deposit (Amdan)
    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 15),
        account_id="CUST-0001",
        amount=25000.0,
        description="Advance deposit for brick supply",
        payment_method="Cash"
    )
    assert succ is True, f"Failed to save Amdan: {msg}"
    assert res is not None
    assert res["TransactionNo"].startswith("RCT-")

    # 3. Cash must increase by 25,000
    after_cash = MoneyTransactionService.get_cash_summary()["net_cash"]
    assert after_cash == init_cash + 25000.0

    # 4. Customer ledger must reflect Credit of 25,000
    ledger = LedgerService.calculate_worker_ledger("CUST-0001", date(2026, 8, 1), date(2026, 8, 20))
    assert ledger is not None
    matching_txns = [t for t in ledger["transactions"] if t["ref"] == res["TransactionNo"]]
    assert len(matching_txns) == 1
    assert matching_txns[0]["credit"] == 25000.0
    assert matching_txns[0]["debit"] == 0.0


def test_create_akrajat_payment_labour():
    """Verify labour Akrajat (payment/advance) decreases cash and debits labour khata."""
    # First inject enough cash via customer receipt
    MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 1),
        account_id="CUST-0001",
        amount=50000.0,
        description="Cash float injection",
        payment_method="Cash"
    )

    cash_before = MoneyTransactionService.get_cash_summary()["net_cash"]

    # Record Akrajat to Pathera Labourer
    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="PAYMENT",
        txn_date=date(2026, 8, 16),
        account_id="WRK-0001",
        amount=7000.0,
        description="Weekly advance for brick molding",
        payment_method="Cash"
    )
    assert succ is True, f"Failed to save Akrajat: {msg}"
    assert res["TransactionNo"].startswith("PAY-")

    # Cash must decrease by 7,000
    cash_after = MoneyTransactionService.get_cash_summary()["net_cash"]
    assert cash_after == cash_before - 7000.0

    # Labour ledger must reflect Debit of 7,000
    ledger = LedgerService.calculate_worker_ledger("WRK-0001", date(2026, 8, 1), date(2026, 8, 20))
    assert ledger is not None
    matching_txns = [t for t in ledger["transactions"] if t["ref"] == res["TransactionNo"]]
    assert len(matching_txns) == 1
    assert matching_txns[0]["debit"] == 7000.0
    assert matching_txns[0]["credit"] == 0.0


def test_negative_cash_guard_for_munshi():
    """Verify Munshi cannot make a cash payment if cash in hand is insufficient."""
    # Switch session to Munshi
    current_session.login(2, "munshi", "Munshi Ali", "Munshi")

    # Attempt to disburse Rs. 500,000 cash when cash is nowhere near that
    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="PAYMENT",
        txn_date=date(2026, 8, 16),
        account_id="WRK-0001",
        amount=500000.0,
        description="Massive cash payout",
        payment_method="Cash"
    )
    assert succ is False
    assert "Insufficient Cash" in msg or "not allowed to overdraw" in msg


def test_labour_advance_recovery_amdan():
    """Verify labourer returning advance debt (Amdan) credits labour account and increases cash."""
    cash_before = MoneyTransactionService.get_cash_summary()["net_cash"]

    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 18),
        account_id="WRK-0001",
        amount=3500.0,
        description="Return of seasonal advance debt",
        payment_method="Cash"
    )
    assert succ is True

    # Cash increased
    assert MoneyTransactionService.get_cash_summary()["net_cash"] == cash_before + 3500.0

    # Worker Khata has credit of 3,500
    ledger = LedgerService.calculate_worker_ledger("WRK-0001", date(2026, 8, 1), date(2026, 8, 20))
    matching_txns = [t for t in ledger["transactions"] if t["ref"] == res["TransactionNo"]]
    assert len(matching_txns) == 1
    assert matching_txns[0]["credit"] == 3500.0


def test_customer_refund_akrajat():
    """Verify customer refund (Akrajat) debits customer account."""
    # Inject cash first
    MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 1),
        account_id="CUST-0001",
        amount=20000.0,
        description="Float deposit",
        payment_method="Cash"
    )

    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="PAYMENT",
        txn_date=date(2026, 8, 19),
        account_id="CUST-0001",
        amount=4000.0,
        description="Refund for cancelled order items",
        payment_method="Cash"
    )
    assert succ is True

    # Customer ledger has Debit of 4,000
    ledger = LedgerService.calculate_worker_ledger("CUST-0001", date(2026, 8, 1), date(2026, 8, 20))
    matching_txns = [t for t in ledger["transactions"] if t["ref"] == res["TransactionNo"]]
    assert len(matching_txns) == 1
    assert matching_txns[0]["debit"] == 4000.0


def test_rbac_munshi_cannot_delete_admin_can():
    """Verify Munshi cannot delete financial transactions, but Admin can reverse them."""
    # 1. Create a transaction as Admin
    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 20),
        account_id="CUST-0001",
        amount=15000.0,
        description="Deposit to test deletion",
        payment_method="Cash"
    )
    t_id = res["TransactionID"]

    # 2. Switch to Munshi
    current_session.login(2, "munshi", "Munshi Ali", "Munshi")
    succ_del, msg_del = MoneyTransactionService.delete_transaction(t_id)
    assert succ_del is False
    assert "Munshi cannot delete" in msg_del

    # 3. Switch back to Admin
    current_session.login(1, "admin", "System Administrator", "Administrator")
    cash_before = MoneyTransactionService.get_cash_summary()["net_cash"]

    succ_del_adm, msg_del_adm = MoneyTransactionService.delete_transaction(t_id, reason="Reversal test")
    assert succ_del_adm is True
    assert "safely deleted" in msg_del_adm

    # Cash must reverse by 15,000
    cash_after = MoneyTransactionService.get_cash_summary()["net_cash"]
    assert cash_after == cash_before - 15000.0


def test_atomic_validation_and_integrity():
    """Verify invalid amounts or non-existent accounts are rejected without polluting database."""
    # Negative amount
    succ, msg, res = MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 20),
        account_id="CUST-0001",
        amount=-500.0,
        description="Invalid negative amount",
        payment_method="Cash"
    )
    assert succ is False
    assert "greater than zero" in msg

    # Non-existent account
    succ2, msg2, res2 = MoneyTransactionService.save_transaction(
        txn_type="RECEIPT",
        txn_date=date(2026, 8, 20),
        account_id="NON-EXISTENT-9999",
        amount=1000.0,
        description="Ghost account",
        payment_method="Cash"
    )
    assert succ2 is False
    assert "does not exist" in msg2
