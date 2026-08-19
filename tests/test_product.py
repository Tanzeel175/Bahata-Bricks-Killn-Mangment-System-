import pytest
from app.database.init_db import init_db
from app.services.auth_service import AuthService
from app.services.product_service import ProductService


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


def test_default_product_categories_seeded():
    categories = ProductService.get_all_categories()
    cat_names = [c["CategoryName"] for c in categories]
    assert "Purchase" in cat_names
    assert "Sale" in cat_names
    assert "Molding" in cat_names


def test_product_creation_and_multi_category_assignment():
    categories = ProductService.get_all_categories()
    cat_map = {c["CategoryName"]: c["CategoryID"] for c in categories}

    # 1. Create Coal (Purchase)
    success, msg = ProductService.save_product(
        data={"ProductName": "Coal", "Description": "High grade steam coal"},
        selected_category_ids=[cat_map["Purchase"]],
        is_edit_mode=False
    )
    assert success is True
    assert "created successfully" in msg

    # 2. Create Clay (Purchase + Molding multi-category)
    success2, msg2 = ProductService.save_product(
        data={"ProductName": "Clay", "Description": "Raw brick clay"},
        selected_category_ids=[cat_map["Purchase"], cat_map["Molding"]],
        is_edit_mode=False
    )
    assert success2 is True

    # Search and verify
    products = ProductService.search_products(query_str="Clay")
    assert len(products) == 1
    assert "Purchase" in products[0]["CategoryNames"]
    assert "Molding" in products[0]["CategoryNames"]


def test_product_rate_and_stock_calculation():
    categories = ProductService.get_all_categories()
    cat_id = categories[0]["CategoryID"]

    data = {
        "ProductName": "Paki Brick Special",
        "UnitRate": 14.50,
        "StockQuantity": 5000,
        "Description": "Premium quality baked brick"
    }

    success, msg = ProductService.save_product(data, [cat_id], is_edit_mode=False)
    assert success is True

    products = ProductService.search_products(query_str="Paki Brick Special")
    assert len(products) == 1
    p = products[0]
    assert p["UnitRate"] == 14.50
    assert p["StockQuantity"] == 5000
    assert p["TotalStockValue"] == 14.50 * 5000  # 72,500.00


def test_duplicate_product_name_rejection():
    categories = ProductService.get_all_categories()
    cat_id = categories[0]["CategoryID"]

    # First creation
    ProductService.save_product({"ProductName": "Paki Brick"}, [cat_id])

    # Second creation with same name
    success, msg = ProductService.save_product({"ProductName": "Paki Brick"}, [cat_id])
    assert success is False
    assert "already exists" in msg


def test_dynamic_category_product_lookup():
    categories = ProductService.get_all_categories()
    cat_map = {c["CategoryName"]: c["CategoryID"] for c in categories}

    # Add products
    ProductService.save_product({"ProductName": "Coal"}, [cat_map["Purchase"]])
    ProductService.save_product({"ProductName": "Paki Brick"}, [cat_map["Sale"]])
    ProductService.save_product({"ProductName": "Clay"}, [cat_map["Purchase"], cat_map["Molding"]])

    # Dynamic lookup for Purchase module
    purchase_products = ProductService.get_products_by_category("Purchase")
    purchase_names = [p["ProductName"] for p in purchase_products]
    assert "Coal" in purchase_names
    assert "Clay" in purchase_names
    assert "Paki Brick" not in purchase_names

    # Dynamic lookup for Sale module
    sale_products = ProductService.get_products_by_category("Sale")
    sale_names = [p["ProductName"] for p in sale_products]
    assert "Paki Brick" in sale_names
    assert "Coal" not in sale_names

    # Dynamic lookup for Molding module
    molding_products = ProductService.get_products_by_category("Molding")
    molding_names = [p["ProductName"] for p in molding_products]
    assert "Clay" in molding_names
    assert "Coal" not in molding_names


def test_munshi_delete_permission_denied():
    categories = ProductService.get_all_categories()
    cat_id = categories[0]["CategoryID"]

    success, _ = ProductService.save_product({"ProductName": "Kacchi Brick"}, [cat_id])
    products = ProductService.search_products(query_str="Kacchi Brick")
    pid = products[0]["ProductID"]

    # Switch session to Munshi
    AuthService.authenticate("munshi", "Munshi@123")

    # Attempt delete
    del_success, del_msg = ProductService.delete_product(pid)
    assert del_success is False
    assert "Access Denied" in del_msg
