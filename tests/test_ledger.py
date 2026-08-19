import pytest
from datetime import date, timedelta
from app.database.init_db import init_db
from app.database.connection import get_db_session
from app.database.schema import AccountType, LabourAccount, Product
from app.services.labour_service import LabourService
from app.services.product_service import ProductService
from app.services.production_service import ProductionService
from app.services.ledger_service import LedgerService
from app.security.session import current_session


@pytest.fixture(autouse=True)
def setup_test_database():
    """Reset and seed fresh test database for each test case."""
    init_db()
    current_session.login(1, "admin", "System Administrator", "Administrator")
    yield
    current_session.logout()


def test_ledger_categories_and_worker_lookup():
    categories = LedgerService.get_supported_categories()
    assert "Pathera" in categories
    assert "Bahri Wala" in categories
    assert "Nakkasi Wala" in categories

    pathera_workers = LedgerService.get_workers_by_category("Pathera")
    assert len(pathera_workers) > 0
    assert any(w["WorkerID"] == "WRK-0001" for w in pathera_workers)


def test_pathera_ledger_calculation():
    with get_db_session() as session:
        pathera_type = session.query(AccountType).filter_by(AccountTypeName="Pathera").first()
        prod = session.query(Product).filter_by(ProductName="Kacchi Brick (Pathera)").first()
        tid = pathera_type.AccountTypeID
        pid = prod.ProductID

    # 1. Create a worker
    wid = LabourService.generate_worker_id()
    succ_acc, msg_acc = LabourService.save_account({
        "WorkerID": wid,
        "AccountTypeID": tid,
        "EnglishName": "Test Pathera Worker",
        "CNIC": "35202-7777777-1",
        "Mobile": "0300-7777777",
        "ReferenceName": "Chaudhry Ahmad",
        "ReferenceMobile": "0300-8888888"
    })
    assert succ_acc is True, f"Failed to save account: {msg_acc}"

    # 2. Set worker rate: 1,600 PKR per 1,000
    ProductionService.save_worker_rates(wid, {pid: 1600.0})

    # 3. Add Production Entry: 10,000 bricks on 2026-08-01 -> Credit = 16,000.00
    ProductionService.save_production_entry(
        entry_date=date(2026, 8, 1),
        account_type_id=tid,
        remarks="Batch 1",
        details_list=[{"WorkerID": wid, "ProductID": pid, "Quantity": 10000.0}]
    )

    # 4. Add Payment Entry: Rs. 5,000 cash paid on 2026-08-05 -> Debit = 5,000.00
    succ, msg = LedgerService.save_labour_payment(
        worker_id=wid,
        payment_date=date(2026, 8, 5),
        amount=5000.0,
        payment_type="Cash Payment",
        remarks="Weekly advance"
    )
    assert succ is True

    # 5. Calculate Ledger report from 2026-08-01 to 2026-08-10
    report = LedgerService.calculate_worker_ledger(wid, date(2026, 8, 1), date(2026, 8, 10))
    assert report is not None
    assert report["opening_balance"] == 0.0
    assert report["total_credit"] == 16000.0
    assert report["total_debit"] == 5000.0
    assert report["closing_balance"] == 11000.0
    assert report["statement_status"] == "PAYABLE"
    assert "AMOUNT PAYABLE TO LABOUR: Rs. 11,000.00" in report["statement_label"]

    txns = report["transactions"]
    assert len(txns) == 2
    assert txns[0]["credit"] == 16000.0
    assert txns[0]["running_balance"] == 16000.0
    assert txns[1]["debit"] == 5000.0
    assert txns[1]["running_balance"] == 11000.0


def test_opening_balance_calculation_before_from_date():
    with get_db_session() as session:
        pathera_type = session.query(AccountType).filter_by(AccountTypeName="Pathera").first()
        prod = session.query(Product).filter_by(ProductName="Kacchi Brick (Pathera)").first()
        tid = pathera_type.AccountTypeID
        pid = prod.ProductID

    wid = LabourService.generate_worker_id()
    succ_acc, msg_acc = LabourService.save_account({
        "WorkerID": wid,
        "AccountTypeID": tid,
        "EnglishName": "Opening Balance Worker",
        "CNIC": "35202-6666666-1",
        "Mobile": "0300-6666666",
        "ReferenceName": "Self",
        "ReferenceMobile": "0300-8888888"
    })
    assert succ_acc is True, f"Failed to save account: {msg_acc}"

    ProductionService.save_worker_rates(wid, {pid: 1500.0})

    # Prior production on July 25 (10,000 @ 1,500 = 15,000 Credit)
    ProductionService.save_production_entry(
        entry_date=date(2026, 7, 25),
        account_type_id=tid,
        remarks="July Batch",
        details_list=[{"WorkerID": wid, "ProductID": pid, "Quantity": 10000.0}]
    )

    # Prior payment on July 28 (Rs. 3,000 Debit)
    LedgerService.save_labour_payment(wid, date(2026, 7, 28), 3000.0, "Cash Payment", "Advance")

    # August 2 production (5,000 @ 1,500 = 7,500 Credit)
    ProductionService.save_production_entry(
        entry_date=date(2026, 8, 2),
        account_type_id=tid,
        remarks="August Batch",
        details_list=[{"WorkerID": wid, "ProductID": pid, "Quantity": 5000.0}]
    )

    # Calculate ledger for August period: 2026-08-01 to 2026-08-31
    report = LedgerService.calculate_worker_ledger(wid, date(2026, 8, 1), date(2026, 8, 31))
    assert report["opening_balance"] == 12000.0  # 15,000 Credit - 3,000 Debit prior
    assert report["total_credit"] == 7500.0
    assert report["total_debit"] == 0.0
    assert report["closing_balance"] == 19500.0  # 12,000 Opening + 7,500 Period Credit
    assert len(report["transactions"]) == 1


def test_global_wheel_filter():
    from app.ui.components.wheel_filter import GlobalFocusWheelEventFilter
    from PySide6.QtWidgets import QComboBox, QApplication
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPoint, QPointF, Qt, QEvent

    app = QApplication.instance() or QApplication([])
    filter_obj = GlobalFocusWheelEventFilter()

    cb = QComboBox()
    cb.addItems(["Option A", "Option B", "Option C"])
    cb.setCurrentIndex(0)
    cb.clearFocus()

    # Create dummy wheel event
    wheel_ev = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False
    )

    # When unfocused, filter intercepts event
    filtered = filter_obj.eventFilter(cb, wheel_ev)
    assert filtered is True
    assert cb.currentIndex() == 0  # Not changed!

