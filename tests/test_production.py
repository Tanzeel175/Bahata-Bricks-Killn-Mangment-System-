from datetime import date
import pytest
from app.database.init_db import init_db
from app.services.auth_service import AuthService
from app.services.labour_service import LabourService
from app.services.product_service import ProductService
from app.services.production_service import ProductionService


@pytest.fixture(autouse=True)
def setup_db_and_auth():
    from app.database.schema import Base
    from app.database.connection import get_engine
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    # Authenticate as admin by default
    AuthService.authenticate("admin", "Admin@123")
    yield
    AuthService.logout()


def helper_create_labour_worker(name: str, cnic: str) -> str:
    types = LabourService.get_account_types()
    pathera_type = next(t for t in types if t["AccountTypeName"] == "Pathera")

    w_id = LabourService.generate_worker_id()
    acc_data = {
        "WorkerID": w_id,
        "AccountTypeID": pathera_type["AccountTypeID"],
        "EnglishName": name,
        "UrduName": "علی رضا",
        "CNIC": cnic,
        "Mobile": "03001234567",
        "ReferenceName": "Chaudhry Ahmad",
        "ReferenceMobile": "03008888888"
    }
    success, res = LabourService.save_account(acc_data, is_edit_mode=False)
    assert success is True, f"Failed to save account: {res}"
    return w_id


def test_labour_rate_management():
    worker_id = helper_create_labour_worker("Ali Raza Test", "35202-9999991-1")

    # Get Molding category products
    categories = ProductService.get_all_categories()
    molding_cat = next(c for c in categories if c["CategoryName"] == "Molding")

    # Create Kacchi Brick product
    ProductService.save_product(
        data={"ProductName": "Kacchi Brick", "Description": "Molding product"},
        selected_category_ids=[molding_cat["CategoryID"]],
        is_edit_mode=False
    )
    products = ProductService.get_products_by_category("Molding")
    kacchi_brick = next(p for p in products if p["ProductName"] == "Kacchi Brick")

    # Set rate: 900 PKR per 1,000 units
    rate_success, msg = ProductionService.save_worker_rates(worker_id, {kacchi_brick["ProductID"]: 900.0})
    assert rate_success is True

    rates = ProductionService.get_worker_rates(worker_id)
    assert rates.get(kacchi_brick["ProductID"]) == 900.0


def test_production_entry_creation():
    worker_id = helper_create_labour_worker("Muhammad Usman Test", "35202-9999992-1")

    types = LabourService.get_account_types()
    pathera_type = next(t for t in types if t["AccountTypeName"] == "Pathera")

    categories = ProductService.get_all_categories()
    molding_cat = next(c for c in categories if c["CategoryName"] == "Molding")
    ProductService.save_product(
        data={"ProductName": "Kacchi Brick Special"},
        selected_category_ids=[molding_cat["CategoryID"]]
    )
    products = ProductService.get_products_by_category("Molding")
    prod = next(p for p in products if p["ProductName"] == "Kacchi Brick Special")

    # Set rate 900 PKR per 1,000
    ProductionService.save_worker_rates(worker_id, {prod["ProductID"]: 900.0})

    # Save Production Entry for 12,000 bricks
    details_list = [
        {"WorkerID": worker_id, "ProductID": prod["ProductID"], "Quantity": 12000.0}
    ]
    succ, msg = ProductionService.save_production_entry(
        entry_date=date.today(),
        account_type_id=pathera_type["AccountTypeID"],
        remarks="First shift production",
        details_list=details_list,
        is_edit_mode=False
    )
    assert succ is True


def test_production_entry_update():
    types = LabourService.get_account_types()
    pathera_type = types[0]

    worker_id = helper_create_labour_worker("Tariq Ali Test", "35202-9999993-1")

    categories = ProductService.get_all_categories()
    molding_cat = next(c for c in categories if c["CategoryName"] == "Molding")
    ProductService.save_product({"ProductName": "Kacchi Tile"}, [molding_cat["CategoryID"]])
    prod = next(p for p in ProductService.get_products_by_category("Molding") if p["ProductName"] == "Kacchi Tile")

    # Rate 1,000 PKR per 1,000
    ProductionService.save_worker_rates(worker_id, {prod["ProductID"]: 1000.0})

    # Save initial 10,000
    ProductionService.save_production_entry(
        entry_date=date.today(),
        account_type_id=pathera_type["AccountTypeID"],
        remarks="Initial batch",
        details_list=[{"WorkerID": worker_id, "ProductID": prod["ProductID"], "Quantity": 10000.0}]
    )
    history = ProductionService.search_production_entries()
    prod_id = history[0]["ProductionID"]

    # Update to 15,000
    succ, _ = ProductionService.save_production_entry(
        entry_date=date.today(),
        account_type_id=pathera_type["AccountTypeID"],
        remarks="Updated batch",
        details_list=[{"WorkerID": worker_id, "ProductID": prod["ProductID"], "Quantity": 15000.0}],
        production_id=prod_id,
        is_edit_mode=True
    )
    assert succ is True


def test_production_entry_delete():
    types = LabourService.get_account_types()
    pathera_type = types[0]

    worker_id = helper_create_labour_worker("Zubair Ahmad Test", "35202-9999994-1")

    categories = ProductService.get_all_categories()
    molding_cat = next(c for c in categories if c["CategoryName"] == "Molding")
    ProductService.save_product({"ProductName": "Kacchi Brick (Pathera Delete Test)"}, [molding_cat["CategoryID"]])
    prod = next(p for p in ProductService.get_products_by_category("Molding") if p["ProductName"] == "Kacchi Brick (Pathera Delete Test)")

    ProductionService.save_worker_rates(worker_id, {prod["ProductID"]: 800.0})

    # Save production entry
    ProductionService.save_production_entry(
        entry_date=date.today(),
        account_type_id=pathera_type["AccountTypeID"],
        remarks="Temporary batch",
        details_list=[{"WorkerID": worker_id, "ProductID": prod["ProductID"], "Quantity": 5000.0}]
    )
    history = ProductionService.search_production_entries()
    prod_id = history[0]["ProductionID"]

    # Delete entry as admin
    AuthService.authenticate("admin", "Admin@123")
    del_succ, msg = ProductionService.delete_production_entry(prod_id)
    assert del_succ is True


def test_munshi_cannot_delete_production_entry():
    # Login as munshi
    AuthService.authenticate("munshi", "Munshi@123")

    del_succ, msg = ProductionService.delete_production_entry(1)
    assert del_succ is False
    assert "Access Denied" in msg


def test_get_production_entry_by_date_and_category():
    worker_id = helper_create_labour_worker("Date Lookup Worker", "35202-8888888-8")
    types = LabourService.get_account_types()
    pathera_type = next(t for t in types if t["AccountTypeName"] == "Pathera")
    categories = ProductService.get_all_categories()
    molding_cat = next(c for c in categories if c["CategoryName"] == "Molding")
    prod = next(p for p in ProductService.get_products_by_category("Molding") if p["ProductName"] == "Kacchi Brick (Pathera)")

    test_date = date(2026, 8, 8)
    ProductionService.save_worker_rates(worker_id, {prod["ProductID"]: 1600.0})
    save_succ, msg = ProductionService.save_production_entry(
        entry_date=test_date,
        account_type_id=pathera_type["AccountTypeID"],
        remarks="Date lookup test batch",
        details_list=[{"WorkerID": worker_id, "ProductID": prod["ProductID"], "Quantity": 15000.0}]
    )
    assert save_succ is True, f"Failed to save production entry: {msg}"

    entry = ProductionService.get_production_entry_by_date_and_category(test_date, pathera_type["AccountTypeID"])
    assert entry is not None
    assert entry["EntryDate"] == "2026-08-08"
    assert entry["AccountTypeID"] == pathera_type["AccountTypeID"]
    assert entry["Remarks"] == "Date lookup test batch"
    assert len(entry["Details"]) == 1
    assert entry["Details"][0]["Quantity"] == 15000.0


def test_pathera_cannot_produce_baked_bricks():
    worker_id = helper_create_labour_worker("Pathera Invalid Prod Worker", "35202-7777777-7")
    types = LabourService.get_account_types()
    pathera_type = next(t for t in types if t["AccountTypeName"] == "Pathera")

    products = ProductService.get_products_by_category("Molding")
    awal_prod = next(p for p in products if p["ProductName"] == "Awal")

    # Set rate
    ProductionService.save_worker_rates(worker_id, {awal_prod["ProductID"]: 1600.0})

    # Attempt to save production entry for Pathera with Awal (baked brick)
    succ, msg = ProductionService.save_production_entry(
        entry_date=date.today(),
        account_type_id=pathera_type["AccountTypeID"],
        remarks="Should fail due to category restriction",
        details_list=[{"WorkerID": worker_id, "ProductID": awal_prod["ProductID"], "Quantity": 10000.0}]
    )
    assert succ is False
    assert "Category Restriction" in msg
    assert "Pathera can ONLY mold raw unbaked bricks/tiles" in msg
