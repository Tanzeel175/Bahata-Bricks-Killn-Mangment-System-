import logging
from datetime import datetime, date
from app.database.schema import (
    Base, Role, User, AccountType, ProductCategory, Product, ProductCategoryMapping,
    LabourAccount, LabourRate, ProductionHeader, ProductionDetail, LabourPayment
)
from app.database.connection import get_engine, get_db_session
from app.security.hashing import hash_password

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNT_TYPES = [
    "Pathera",
    "Nakkasi Wala",
    "Bahari Wala",
    "Pathera Jamadar",
    "Nakkasi Jamadar",
    "Purchase Party",
    "Customer",
    "Owner",
    "Transporter",
    "Worker",
    "Mutfariq Expenses",
    "Salesman",
    "Mutfariq Income",
    "Cashier",
    "Others",
    "Fixed Assets",
    "Other Source",
    "Driver"
]


def _migrate_schema(engine):
    """Safely adds missing columns to existing SQLite tables if schema has evolved."""
    try:
        with engine.connect() as conn:
            cursor = conn.exec_driver_sql("PRAGMA table_info(SalesHeader);")
            columns = [row[1] for row in cursor.fetchall()]
            if columns:
                if "TransportMode" not in columns:
                    conn.exec_driver_sql("ALTER TABLE SalesHeader ADD COLUMN TransportMode VARCHAR(50);")
                if "VehicleNumber" not in columns:
                    conn.exec_driver_sql("ALTER TABLE SalesHeader ADD COLUMN VehicleNumber VARCHAR(50);")
                if "DriverName" not in columns:
                    conn.exec_driver_sql("ALTER TABLE SalesHeader ADD COLUMN DriverName VARCHAR(100);")
            conn.commit()
    except Exception as e:
        logger.warning(f"Schema migration warning: {e}")


def init_db():
    """Create tables if they don't exist and seed initial data."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_schema(engine)

    with get_db_session() as session:
        # Seed Roles
        admin_role = session.query(Role).filter_by(RoleName="Administrator").first()
        if not admin_role:
            admin_role = Role(RoleName="Administrator")
            session.add(admin_role)

        munshi_role = session.query(Role).filter_by(RoleName="Munshi").first()
        if not munshi_role:
            munshi_role = Role(RoleName="Munshi")
            session.add(munshi_role)

        session.flush()

        # Seed Default Admin User
        default_admin = session.query(User).filter_by(Username="admin").first()
        if not default_admin:
            hashed = hash_password("Admin@123")
            admin_user = User(
                Username="admin",
                PasswordHash=hashed,
                FullName="System Administrator",
                Email="admin@bahtakiln.com",
                Mobile="03001234567",
                RoleID=admin_role.RoleID,
                IsActive=True,
                IsLocked=False,
                CreatedBy="SYSTEM"
            )
            session.add(admin_user)
            logger.info("Default admin user created ('admin' / 'Admin@123').")

        # Seed Default Munshi User for testing convenience
        default_munshi = session.query(User).filter_by(Username="munshi").first()
        if not default_munshi:
            hashed = hash_password("Munshi@123")
            munshi_user = User(
                Username="munshi",
                PasswordHash=hashed,
                FullName="Munshi Ali",
                Email="munshi@bahtakiln.com",
                Mobile="03007654321",
                RoleID=munshi_role.RoleID,
                IsActive=True,
                IsLocked=False,
                CreatedBy="SYSTEM"
            )
            session.add(munshi_user)
            logger.info("Default munshi user created ('munshi' / 'Munshi@123').")

        # Seed Account Types
        for type_name in DEFAULT_ACCOUNT_TYPES:
            existing = session.query(AccountType).filter_by(AccountTypeName=type_name).first()
            if not existing:
                account_type = AccountType(AccountTypeName=type_name, IsSystemDefined=True)
                session.add(account_type)

        # Seed Default Product Categories
        default_categories = ["Purchase", "Sale", "Molding"]
        for cat_name in default_categories:
            existing_cat = session.query(ProductCategory).filter_by(CategoryName=cat_name).first()
            if not existing_cat:
                cat = ProductCategory(CategoryName=cat_name)
                session.add(cat)

        session.flush()

        # Seed Default Products mapped to Molding and Sale categories
        molding_cat = session.query(ProductCategory).filter_by(CategoryName="Molding").first()
        sale_cat = session.query(ProductCategory).filter_by(CategoryName="Sale").first()

        # Delete legacy generic Kacchi products if they exist
        legacy_prods = session.query(Product).filter(Product.ProductName.in_(["Kacchi Brick", "Kacchi Tile"])).all()
        for lp in legacy_prods:
            session.delete(lp)
        session.flush()

        default_molding_products = [
            "Kacchi Brick (Pathera)", "Kacchi Brick (Bahari)",
            "Kacchi Tile (Pathera)", "Kacchi Tile (Bahari)",
            "Awal", "Doam", "Khinger", "Tile"
        ]
        for prod_name in default_molding_products:
            p = session.query(Product).filter_by(ProductName=prod_name).first()
            if not p:
                p = Product(
                    ProductName=prod_name,
                    Description=f"Standard {prod_name}",
                    UnitRate=14000.0 if prod_name == "Awal" else 10000.0,
                    IsSystemProduct=True
                )
                session.add(p)
                session.flush()
            else:
                p.IsSystemProduct = True

            if molding_cat:
                if not session.query(ProductCategoryMapping).filter_by(ProductID=p.ProductID, CategoryID=molding_cat.CategoryID).first():
                    session.add(ProductCategoryMapping(ProductID=p.ProductID, CategoryID=molding_cat.CategoryID))

            if sale_cat:
                if not session.query(ProductCategoryMapping).filter_by(ProductID=p.ProductID, CategoryID=sale_cat.CategoryID).first():
                    session.add(ProductCategoryMapping(ProductID=p.ProductID, CategoryID=sale_cat.CategoryID))

        session.flush()

        # --- SEED COMPREHENSIVE DUMMY DATA FOR TESTING & PREVIEW ---
        seed_dummy_data(session)

        session.commit()
        logger.info("Database initialized and seeded successfully.")


def seed_dummy_data(session):
    """Seed sample workers, customers, labour rates, production entries, and khata ledger records."""
    pathera_type = session.query(AccountType).filter_by(AccountTypeName="Pathera").first()
    bahari_type = session.query(AccountType).filter_by(AccountTypeName="Bahari Wala").first()
    nakkasi_type = session.query(AccountType).filter_by(AccountTypeName="Nakkasi Wala").first()
    customer_type = session.query(AccountType).filter_by(AccountTypeName="Customer").first()

    if not pathera_type or not bahari_type or not nakkasi_type or not customer_type:
        return

    # 1. Dummy Workers & Customers
    dummy_workers = [
        # Patheras
        ("WRK-0001", pathera_type.AccountTypeID, "Muhammad Ali", "محمد علی", "Muhammad Boota", "35202-1111111-1", "0300-1111111", "Molding Line A, Kiln Yard"),
        ("WRK-0002", pathera_type.AccountTypeID, "Tariq Mehmood", "طارق محمود", "Chaudhry Bashir", "35202-2222222-2", "0301-2222222", "Molding Line B, Kiln Yard"),
        ("WRK-0003", pathera_type.AccountTypeID, "Rashid Khan", "راشد خان", "Gul Khan", "35202-3333333-3", "0302-3333333", "Molding Line C, Kiln Yard"),
        ("WRK-0004", pathera_type.AccountTypeID, "Allah Ditta", "اللہ دتہ", "Faqir Muhammad", "35202-4444444-4", "0303-4444444", "Molding Line D, Kiln Yard"),
        # Bahari Walas
        ("WRK-0005", bahari_type.AccountTypeID, "Ghulam Mustafa", "غلام مصطفی", "Inayat Ali", "35202-5555555-5", "0304-5555555", "Kiln Loading Sector 1"),
        ("WRK-0006", bahari_type.AccountTypeID, "Sajjad Hussain", "سجاد حسین", "Khadim Hussain", "35202-6666666-6", "0305-6666666", "Kiln Loading Sector 2"),
        # Nakkasi Walas
        ("WRK-0007", nakkasi_type.AccountTypeID, "Zulqarnain Shah", "ذوالقرنین شاہ", "Syed Akbar Shah", "35202-7777777-7", "0306-7777777", "Unloading Grid 1"),
        ("WRK-0008", nakkasi_type.AccountTypeID, "Imtiaz Ali", "امتیاز علی", "Barkat Ali", "35202-8888888-8", "0307-8888888", "Unloading Grid 2"),
        # Customers
        ("CUST-0001", customer_type.AccountTypeID, "Haji Construction Company", "حاجی کنسٹرکشن", "Haji Abdul Rehman", "35202-9999999-9", "0308-9999999", "Main Boulevard, Lahore"),
        ("CUST-0002", customer_type.AccountTypeID, "Al-Madina Builders", "المدینہ بلڈرز", "Chaudhry Akram", "35202-8888111-1", "0309-8888111", "G.T. Road, Gujranwala")
    ]

    for wid, tid, en_name, ur_name, f_name, cnic, mob, addr in dummy_workers:
        if not session.query(LabourAccount).filter_by(WorkerID=wid).first():
            w = LabourAccount(
                WorkerID=wid,
                AccountTypeID=tid,
                EnglishName=en_name,
                UrduName=ur_name,
                FatherName=f_name,
                CNIC=cnic,
                Mobile=mob,
                ReferenceName="Self",
                ReferenceMobile="N/A",
                Address=addr,
                DailyModularTarget=1000,
                DailyFillerTarget=0,
                CreatedBy="SYSTEM"
            )
            session.add(w)

    session.flush()

    # 2. Products
    prod_pathera_brick = session.query(Product).filter_by(ProductName="Kacchi Brick (Pathera)").first()
    prod_pathera_tile = session.query(Product).filter_by(ProductName="Kacchi Tile (Pathera)").first()
    prod_bahari_brick = session.query(Product).filter_by(ProductName="Kacchi Brick (Bahari)").first()
    prod_bahari_tile = session.query(Product).filter_by(ProductName="Kacchi Tile (Bahari)").first()
    prod_awal = session.query(Product).filter_by(ProductName="Awal").first()
    prod_doam = session.query(Product).filter_by(ProductName="Doam").first()
    prod_khinger = session.query(Product).filter_by(ProductName="Khinger").first()

    # 3. Labour Rates
    if prod_pathera_brick and prod_pathera_tile and prod_bahari_brick:
        # Pathera Rates
        rates_to_set = [
            ("WRK-0001", prod_pathera_brick.ProductID, 1600.0),
            ("WRK-0001", prod_pathera_tile.ProductID, 1800.0),
            ("WRK-0002", prod_pathera_brick.ProductID, 1600.0),
            ("WRK-0002", prod_pathera_tile.ProductID, 1800.0),
            ("WRK-0003", prod_pathera_brick.ProductID, 1650.0),
            ("WRK-0003", prod_pathera_tile.ProductID, 1850.0),
            ("WRK-0004", prod_pathera_brick.ProductID, 1600.0),
            # Bahari Rates
            ("WRK-0005", prod_bahari_brick.ProductID, 450.0),
            ("WRK-0005", prod_bahari_tile.ProductID, 500.0),
            ("WRK-0006", prod_bahari_brick.ProductID, 450.0),
            # Nakkasi Rates
            ("WRK-0007", prod_awal.ProductID, 550.0),
            ("WRK-0007", prod_doam.ProductID, 400.0),
            ("WRK-0007", prod_khinger.ProductID, 300.0),
            ("WRK-0008", prod_awal.ProductID, 550.0)
        ]

        for wid, pid, rval in rates_to_set:
            if not session.query(LabourRate).filter_by(WorkerID=wid, ProductID=pid).first():
                lr = LabourRate(WorkerID=wid, ProductID=pid, RatePer1000=rval, CreatedBy="SYSTEM")
                session.add(lr)

    session.flush()

    # 4. Dummy Production Entries & Khata Posting
    if not session.query(ProductionHeader).first():
        # Entry 1: Patheras (2026-07-28)
        p1 = ProductionHeader(
            EntryDate=date(2026, 7, 28),
            AccountTypeID=pathera_type.AccountTypeID,
            Remarks="Morning Shift Molding Batch",
            CreatedBy="admin"
        )
        session.add(p1)
        session.flush()

        d1 = ProductionDetail(ProductionID=p1.ProductionID, WorkerID="WRK-0001", ProductID=prod_pathera_brick.ProductID, Quantity=12000.0)
        d2 = ProductionDetail(ProductionID=p1.ProductionID, WorkerID="WRK-0002", ProductID=prod_pathera_brick.ProductID, Quantity=10000.0)
        d3 = ProductionDetail(ProductionID=p1.ProductionID, WorkerID="WRK-0003", ProductID=prod_pathera_tile.ProductID, Quantity=8000.0)
        session.add_all([d1, d2, d3])

        # 5. Dummy Labour Payments
        if not session.query(LabourPayment).first():
            pay1 = LabourPayment(WorkerID="WRK-0001", PaymentDate=date(2026, 7, 30), PaymentType="Cash Payment", Amount=5000.0, Remarks="Weekly Cash Advance", CreatedBy="admin")
            pay2 = LabourPayment(WorkerID="WRK-0002", PaymentDate=date(2026, 7, 31), PaymentType="Advance Payment", Amount=4000.0, Remarks="Emergency Medical Advance", CreatedBy="admin")
            session.add_all([pay1, pay2])

    session.flush()


if __name__ == "__main__":
    init_db()
