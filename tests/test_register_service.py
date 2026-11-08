from datetime import date, timedelta
import pytest
from app.security.session import current_session
from app.services.register_service import RegisterService
from app.services.ledger_service import LedgerService


@pytest.fixture(autouse=True)
def authenticate_admin():
    current_session.login(
        user_id=1,
        username="admin",
        full_name="Administrator",
        role_name="Administrator"
    )
    yield
    current_session.logout()


def test_supported_categories():
    cats = RegisterService.get_supported_categories()
    assert "Customer" in cats
    assert "Pathera" in cats
    assert "Bahri Wala" in cats
    assert "Nakkasi Wala" in cats

    labour_cats = RegisterService.get_labour_categories()
    assert "Pathera" in labour_cats
    assert "Customer" not in labour_cats


def test_customers_summary_report():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    result = RegisterService.get_customers_summary_report(from_date=from_date, to_date=to_date)
    assert isinstance(result, dict)
    assert "rows" in result
    assert "kpis" in result

    kpis = result["kpis"]
    assert "total_customers" in kpis
    assert "total_sales" in kpis
    assert "total_receipts" in kpis
    assert "total_baqi" in kpis
    assert "total_advance" in kpis

    # Check row structure
    if result["rows"]:
        first = result["rows"][0]
        assert "CustomerID" in first
        assert "EnglishName" in first
        assert "OpeningBalance" in first
        assert "PeriodSales" in first
        assert "PeriodReceipts" in first
        assert "ClosingBalance" in first
        assert "Status" in first
        assert first["Status"] in ("RECEIVABLE", "ADVANCE", "BALANCED")


def test_labour_summary_report():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    # Test All Labour
    res_all = RegisterService.get_labour_summary_report(from_date=from_date, to_date=to_date, category_name="All Labour")
    assert "rows" in res_all
    assert "kpis" in res_all
    assert "total_workers" in res_all["kpis"]
    assert "total_production_qty" in res_all["kpis"]
    assert "total_wages_earned" in res_all["kpis"]

    # Test Category specific: Pathera
    res_pathera = RegisterService.get_labour_summary_report(from_date=from_date, to_date=to_date, category_name="Pathera")
    assert "rows" in res_pathera
    for r in res_pathera["rows"]:
        assert r["CategoryName"] == "Pathera"
        assert "ProductionQty" in r
        assert "EarnedWages" in r
        assert "PaymentsPaid" in r
        assert "ClosingBalance" in r


def test_sales_register():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    sales = RegisterService.get_sales_register(from_date=from_date, to_date=to_date)
    assert "rows" in sales
    assert "kpis" in sales
    assert "total_invoices" in sales["kpis"]
    assert "total_bricks_sold" in sales["kpis"]
    assert "total_sale_amount" in sales["kpis"]

    if sales["rows"]:
        row = sales["rows"][0]
        assert "InvoiceNo" in row
        assert "CustomerName" in row
        assert "TotalBricks" in row
        assert "TotalAmount" in row


def test_production_register():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    prod = RegisterService.get_production_register(from_date=from_date, to_date=to_date)
    assert "rows" in prod
    assert "kpis" in prod
    assert "total_entries" in prod["kpis"]
    assert "total_production_qty" in prod["kpis"]
    assert "total_wages_earned" in prod["kpis"]

    if prod["rows"]:
        row = prod["rows"][0]
        assert "WorkerID" in row
        assert "ProductName" in row
        assert "Quantity" in row
        assert "RatePer1000" in row
        assert "TotalWage" in row


def test_cashbook_register():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    cb = RegisterService.get_cashbook_register(from_date=from_date, to_date=to_date)
    assert "rows" in cb
    assert "kpis" in cb
    assert "opening_cash" in cb["kpis"]
    assert "total_amdan" in cb["kpis"]
    assert "total_akrajat" in cb["kpis"]
    assert "closing_cash" in cb["kpis"]

    if cb["rows"]:
        row = cb["rows"][0]
        assert "TransactionNo" in row
        assert "TransactionType" in row
        assert "AccountName" in row
        assert "Amdan" in row
        assert "Akrajat" in row
        assert "RunningCash" in row


def test_general_accounts_summary():
    today = date.today()
    from_date = date(today.year, 1, 1)
    to_date = today + timedelta(days=1)

    gen = RegisterService.get_general_accounts_summary(
        category_name="Purchase Party",
        from_date=from_date,
        to_date=to_date
    )
    assert "rows" in gen
    assert "kpis" in gen
    assert "total_accounts" in gen["kpis"]
    assert "net_balance" in gen["kpis"]
