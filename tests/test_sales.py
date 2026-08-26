from datetime import date
import pytest
from app.database.init_db import init_db
from app.services.auth_service import AuthService
from app.services.labour_service import LabourService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService
from app.services.ledger_service import LedgerService
from app.database.connection import get_db_session
from app.repositories.payment_repository import PaymentRepository


@pytest.fixture(autouse=True)
def setup_db_and_auth():
    from app.database.schema import Base
    from app.database.connection import get_engine
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    AuthService.authenticate("admin", "Admin@123")
    yield
    AuthService.logout()


def helper_create_customer(name: str, cnic: str = "35202-1111111-1") -> str:
    types = LabourService.get_account_types()
    cust_type = next(t for t in types if t["AccountTypeName"] == "Customer")

    w_id = LabourService.generate_worker_id()
    acc_data = {
        "WorkerID": w_id,
        "AccountTypeID": cust_type["AccountTypeID"],
        "EnglishName": name,
        "UrduName": "حاجی کریم",
        "CNIC": cnic,
        "Mobile": "03001122334",
        "ReferenceName": "Chaudhry Ahmad",
        "ReferenceMobile": "03008888888"
    }
    success, res = LabourService.save_account(acc_data, is_edit_mode=False)
    assert success is True
    return w_id


def test_sales_receipt_creation():
    customer_id = helper_create_customer("Haji Kareem Sales Test")

    # Get Sale products
    products = ProductService.get_products_by_category("Sale")
    awal = next(p for p in products if p["ProductName"] == "Awal")
    doam = next(p for p in products if p["ProductName"] == "Doam")

    items = [
        {"ProductID": awal["ProductID"], "Quantity": 10000.0, "RatePer1000": 14000.0},
        {"ProductID": doam["ProductID"], "Quantity": 5000.0, "RatePer1000": 10000.0}
    ]

    succ, msg, res = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Rehra (ریڑھا)",
        driver_name="Aslam Rehra Wala",
        vehicle_number="Rehra #4",
        remarks="Building Site Sector B",
        items_list=items
    )

    assert succ is True, f"Failed: {msg}"
    assert res is not None
    assert res["TotalAmount"] == (10.0 * 14000.0) + (5.0 * 10000.0)  # 140,000 + 50,000 = 190,000
    assert res["InvoiceNo"].startswith("SAL-")

    # Retrieve and verify
    sale_data = SalesService.get_sale_by_id(res["SaleID"])
    assert sale_data is not None
    assert len(sale_data["Details"]) == 2
    assert sale_data["DriverName"] == "Aslam Rehra Wala"
    assert sale_data["TransportMode"] == "Rehra (ریڑھا)"


def test_customer_khata_ledger_integration():
    customer_id = helper_create_customer("Chaudhry Munir Customer")

    products = ProductService.get_products_by_category("Sale")
    awal = next(p for p in products if p["ProductName"] == "Awal")

    # Save Sales Receipt of 15,000 Awal Bricks @ 14,000/1000 = Rs. 210,000
    succ, msg, res = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Tractor Trolley (ٹریکٹر ٹرالی)",
        driver_name="Rashid Driver",
        vehicle_number="Trolley 98",
        remarks="Delivered to Main Plaza",
        items_list=[{"ProductID": awal["ProductID"], "Quantity": 15000.0, "RatePer1000": 14000.0}]
    )
    assert succ is True

    # Check Customer Khata Ledger
    ledger = LedgerService.calculate_worker_ledger(customer_id, date(2020, 1, 1), date.today())
    assert ledger is not None
    assert ledger["total_debit"] == 210000.0
    assert ledger["total_credit"] == 0.0
    assert ledger["closing_balance"] == -210000.0  # Negative = Receivable from Customer
    assert ledger["statement_status"] == "RECEIVABLE"
    assert "Rashid Driver" in ledger["transactions"][0]["description"]

    # Record Payment received from Customer (Credit = Rs. 150,000)
    with get_db_session() as session:
        pay_repo = PaymentRepository(session)
        pay_repo.add_payment(
            worker_id=customer_id,
            payment_date=date.today(),
            payment_type="Cash Received",
            amount=150000.0,
            remarks="Partial payment received via cash",
            created_by="admin"
        )
        session.commit()

    # Recalculate Ledger
    updated_ledger = LedgerService.calculate_worker_ledger(customer_id, date(2020, 1, 1), date.today())
    assert updated_ledger is not None
    assert updated_ledger["total_debit"] == 210000.0
    assert updated_ledger["total_credit"] == 150000.0
    assert updated_ledger["closing_balance"] == -60000.0  # Remaining Receivable = -Rs. 60,000
    assert updated_ledger["statement_status"] == "RECEIVABLE"


def test_sales_receipt_update():
    customer_id = helper_create_customer("Update Test Customer")
    products = ProductService.get_products_by_category("Sale")
    awal = next(p for p in products if p["ProductName"] == "Awal")

    # Initial Sale: 5,000 bricks @ 14,000 = 70,000
    succ, _, res = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Truck (ٹرک)",
        driver_name="Nawaz",
        vehicle_number="TRK-900",
        remarks="First dispatch",
        items_list=[{"ProductID": awal["ProductID"], "Quantity": 5000.0, "RatePer1000": 14000.0}]
    )
    sale_id = res["SaleID"]

    # Update Sale: 8,000 bricks @ 14,000 = 112,000
    up_succ, up_msg, up_res = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Truck (ٹرک)",
        driver_name="Nawaz",
        vehicle_number="TRK-900",
        remarks="Updated dispatch quantity",
        items_list=[{"ProductID": awal["ProductID"], "Quantity": 8000.0, "RatePer1000": 14000.0}],
        sale_id=sale_id,
        is_edit_mode=True
    )
    assert up_succ is True
    assert up_res["TotalAmount"] == 112000.0

    # Verify updated ledger balance
    ledger = LedgerService.calculate_worker_ledger(customer_id, date(2020, 1, 1), date.today())
    assert ledger["closing_balance"] == -112000.0


def test_sales_receipt_delete_and_permissions():
    customer_id = helper_create_customer("Delete Test Customer")
    products = ProductService.get_products_by_category("Sale")
    awal = next(p for p in products if p["ProductName"] == "Awal")

    succ, _, res = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Rehra",
        driver_name="Rehra Guy",
        vehicle_number="R-1",
        remarks="To be cancelled",
        items_list=[{"ProductID": awal["ProductID"], "Quantity": 2000.0, "RatePer1000": 14000.0}]
    )
    sale_id = res["SaleID"]

    # Munshi cannot delete
    AuthService.authenticate("munshi", "Munshi@123")
    del_succ, msg = SalesService.delete_sales_receipt(sale_id)
    assert del_succ is False
    assert "Access Denied" in msg

    # Admin can delete
    AuthService.authenticate("admin", "Admin@123")
    admin_del_succ, _ = SalesService.delete_sales_receipt(sale_id)
    assert admin_del_succ is True

    # Verify ledger is back to 0
    ledger = LedgerService.calculate_worker_ledger(customer_id, date(2020, 1, 1), date.today())
    assert ledger["closing_balance"] == 0.0


def test_sales_receipt_validation():
    # Customer required
    succ, msg, _ = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id="",
        transport_mode="Rehra",
        driver_name="Test",
        vehicle_number="",
        remarks="",
        items_list=[{"ProductID": 1, "Quantity": 1000.0, "RatePer1000": 14000.0}]
    )
    assert succ is False
    assert "Customer" in msg

    # Items required
    customer_id = helper_create_customer("Validation Customer")
    succ2, msg2, _ = SalesService.save_sales_receipt(
        sale_date=date.today(),
        customer_id=customer_id,
        transport_mode="Rehra",
        driver_name="Test",
        vehicle_number="",
        remarks="",
        items_list=[]
    )
    assert succ2 is False
    assert "item is required" in msg2
