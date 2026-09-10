from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Role(Base):
    __tablename__ = "Roles"

    RoleID = Column(Integer, primary_key=True, autoincrement=True)
    RoleName = Column(String(50), unique=True, nullable=False)

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(RoleID={self.RoleID}, RoleName='{self.RoleName}')>"


class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, autoincrement=True)
    Username = Column(String(50), unique=True, nullable=False, index=True)
    PasswordHash = Column(String(255), nullable=False)
    FullName = Column(String(100), nullable=False)
    Email = Column(String(100), nullable=True)
    Mobile = Column(String(20), nullable=True)
    RoleID = Column(Integer, ForeignKey("Roles.RoleID"), nullable=False)
    IsActive = Column(Boolean, default=True, nullable=False)
    IsLocked = Column(Boolean, default=False, nullable=False)
    FailedAttempts = Column(Integer, default=0, nullable=False)
    MustChangePassword = Column(Boolean, default=False, nullable=False)
    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    LastLogin = Column(DateTime, nullable=True)

    role = relationship("Role", back_populates="users")

    def __repr__(self):
        return f"<User(UserID={self.UserID}, Username='{self.Username}')>"


class AccountType(Base):
    __tablename__ = "AccountTypes"

    AccountTypeID = Column(Integer, primary_key=True, autoincrement=True)
    AccountTypeName = Column(String(100), unique=True, nullable=False, index=True)
    IsSystemDefined = Column(Boolean, default=False, nullable=False)

    labour_accounts = relationship("LabourAccount", back_populates="account_type")

    def __repr__(self):
        return f"<AccountType(ID={self.AccountTypeID}, Name='{self.AccountTypeName}')>"


class LabourAccount(Base):
    __tablename__ = "LabourAccounts"

    WorkerID = Column(String(50), primary_key=True, nullable=False, index=True)
    AccountTypeID = Column(Integer, ForeignKey("AccountTypes.AccountTypeID"), nullable=False)
    EnglishName = Column(String(100), nullable=False, index=True)
    UrduName = Column(String(100), nullable=True)
    FatherName = Column(String(100), nullable=True)
    CNIC = Column(String(20), nullable=False, index=True)
    Mobile = Column(String(20), nullable=False)
    ReferenceName = Column(String(100), nullable=False)
    ReferenceMobile = Column(String(20), nullable=False)
    Address = Column(String(255), nullable=True)
    Email = Column(String(100), nullable=True)
    DailyModularTarget = Column(Float, default=0.0, nullable=False)
    DailyFillerTarget = Column(Float, default=0.0, nullable=False)
    Remarks = Column(String(255), nullable=True)

    # Omit paradigm
    IsOmitted = Column(Boolean, default=False, nullable=False, index=True)
    OmitDate = Column(DateTime, nullable=True)
    OmitReason = Column(String(255), nullable=True)

    # Audit tracking
    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account_type = relationship("AccountType", back_populates="labour_accounts")

    def __repr__(self):
        return f"<LabourAccount(WorkerID='{self.WorkerID}', EnglishName='{self.EnglishName}')>"


class AuditLog(Base):
    __tablename__ = "AuditLogs"

    LogID = Column(Integer, primary_key=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), nullable=True)
    Username = Column(String(50), nullable=True)
    Action = Column(String(100), nullable=False)
    Details = Column(Text, nullable=True)
    Timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    IPAddress = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<AuditLog(Action='{self.Action}', User='{self.Username}', Time={self.Timestamp})>"


class ProductCategory(Base):
    __tablename__ = "ProductCategories"

    CategoryID = Column(Integer, primary_key=True, autoincrement=True)
    CategoryName = Column(String(50), unique=True, nullable=False, index=True)

    product_mappings = relationship("ProductCategoryMapping", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductCategory(ID={self.CategoryID}, Name='{self.CategoryName}')>"


class Product(Base):
    __tablename__ = "Products"

    ProductID = Column(Integer, primary_key=True, autoincrement=True)
    ProductName = Column(String(100), unique=True, nullable=False, index=True)
    Description = Column(String(500), nullable=True)
    UnitRate = Column(Float, default=0.0, nullable=False)
    StockQuantity = Column(Float, default=0.0, nullable=False)
    IsSystemProduct = Column(Boolean, default=False, nullable=False)

    @property
    def TotalStockValue(self) -> float:
        return (self.UnitRate or 0.0) * (self.StockQuantity or 0.0)

    # Audit tracking
    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category_mappings = relationship("ProductCategoryMapping", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(ProductID={self.ProductID}, Name='{self.ProductName}')>"


class ProductCategoryMapping(Base):
    __tablename__ = "ProductCategoryMapping"

    MappingID = Column(Integer, primary_key=True, autoincrement=True)
    ProductID = Column(Integer, ForeignKey("Products.ProductID", ondelete="CASCADE"), nullable=False, index=True)
    CategoryID = Column(Integer, ForeignKey("ProductCategories.CategoryID", ondelete="CASCADE"), nullable=False, index=True)

    product = relationship("Product", back_populates="category_mappings")
    category = relationship("ProductCategory", back_populates="product_mappings")

    def __repr__(self):
        return f"<ProductCategoryMapping(ProductID={self.ProductID}, CategoryID={self.CategoryID})>"


class ProductionHeader(Base):
    __tablename__ = "ProductionHeader"

    ProductionID = Column(Integer, primary_key=True, autoincrement=True)
    EntryDate = Column(Date, nullable=False, index=True)
    AccountTypeID = Column(Integer, ForeignKey("AccountTypes.AccountTypeID"), nullable=False, index=True)
    Remarks = Column(String(255), nullable=True)

    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account_type = relationship("AccountType")
    details = relationship("ProductionDetail", back_populates="header", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductionHeader(ID={self.ProductionID}, Date={self.EntryDate})>"


class ProductionDetail(Base):
    __tablename__ = "ProductionDetail"

    ProductionDetailID = Column(Integer, primary_key=True, autoincrement=True)
    ProductionID = Column(Integer, ForeignKey("ProductionHeader.ProductionID", ondelete="CASCADE"), nullable=False, index=True)
    WorkerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    ProductID = Column(Integer, ForeignKey("Products.ProductID"), nullable=False, index=True)
    Quantity = Column(Float, default=0.0, nullable=False)

    header = relationship("ProductionHeader", back_populates="details")
    worker = relationship("LabourAccount")
    product = relationship("Product")

    def __repr__(self):
        return f"<ProductionDetail(ID={self.ProductionDetailID}, Worker='{self.WorkerID}', ProductID={self.ProductID}, Qty={self.Quantity})>"


class LabourRate(Base):
    __tablename__ = "LabourRates"

    RateID = Column(Integer, primary_key=True, autoincrement=True)
    WorkerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    ProductID = Column(Integer, ForeignKey("Products.ProductID", ondelete="CASCADE"), nullable=False, index=True)
    RatePer1000 = Column(Float, default=0.0, nullable=False)
    EffectiveDate = Column(DateTime, default=datetime.utcnow, nullable=False)

    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    worker = relationship("LabourAccount")
    product = relationship("Product")

    def __repr__(self):
        return f"<LabourRate(Worker='{self.WorkerID}', ProductID={self.ProductID}, RatePer1000={self.RatePer1000})>"


class LabourLedger(Base):
    __tablename__ = "LabourLedger"

    LedgerID = Column(Integer, primary_key=True, autoincrement=True)
    WorkerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    TransactionDate = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ReferenceType = Column(String(50), nullable=False)
    ReferenceID = Column(Integer, nullable=True)
    Description = Column(String(255), nullable=False)
    ProductID = Column(Integer, ForeignKey("Products.ProductID"), nullable=True)
    Quantity = Column(Float, default=0.0, nullable=False)
    Rate = Column(Float, default=0.0, nullable=False)
    Debit = Column(Float, default=0.0, nullable=False)   # Earnings (amount system owes worker)
    Credit = Column(Float, default=0.0, nullable=False)  # Payments (amount paid to worker)
    RunningBalance = Column(Float, default=0.0, nullable=False)

    worker = relationship("LabourAccount")
    product = relationship("Product")

    def __repr__(self):
        return f"<LabourLedger(Worker='{self.WorkerID}', Debit={self.Debit}, Credit={self.Credit}, Balance={self.RunningBalance})>"


class SalesHeader(Base):
    __tablename__ = "SalesHeader"

    SaleID = Column(Integer, primary_key=True, autoincrement=True)
    InvoiceNo = Column(String(50), unique=True, nullable=False, index=True)
    SaleDate = Column(Date, nullable=False, index=True)
    CustomerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID"), nullable=False, index=True)
    TransportMode = Column(String(50), nullable=True)
    VehicleNumber = Column(String(50), nullable=True)
    DriverName = Column(String(100), nullable=True)
    Remarks = Column(String(255), nullable=True)
    TotalAmount = Column(Float, default=0.0, nullable=False)

    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("LabourAccount")
    details = relationship("SalesDetail", back_populates="header", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SalesHeader(ID={self.SaleID}, Invoice='{self.InvoiceNo}', Amount={self.TotalAmount})>"


class SalesDetail(Base):
    __tablename__ = "SalesDetail"

    SaleDetailID = Column(Integer, primary_key=True, autoincrement=True)
    SaleID = Column(Integer, ForeignKey("SalesHeader.SaleID", ondelete="CASCADE"), nullable=False, index=True)
    ProductID = Column(Integer, ForeignKey("Products.ProductID"), nullable=False, index=True)
    Quantity = Column(Float, default=0.0, nullable=False)
    RatePer1000 = Column(Float, default=0.0, nullable=False)
    TotalAmount = Column(Float, default=0.0, nullable=False)

    header = relationship("SalesHeader", back_populates="details")
    product = relationship("Product")

    def __repr__(self):
        return f"<SalesDetail(ID={self.SaleDetailID}, ProductID={self.ProductID}, Qty={self.Quantity}, Total={self.TotalAmount})>"


class ProductInventory(Base):
    __tablename__ = "ProductInventory"

    InventoryID = Column(Integer, primary_key=True, autoincrement=True)
    ProductID = Column(Integer, ForeignKey("Products.ProductID", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    ProducedQuantity = Column(Float, default=0.0, nullable=False)
    SoldQuantity = Column(Float, default=0.0, nullable=False)
    DamagedQuantity = Column(Float, default=0.0, nullable=False)
    CurrentStock = Column(Float, default=0.0, nullable=False)
    MinStockThreshold = Column(Float, default=5000.0, nullable=False)
    LastUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product")

    def __repr__(self):
        return f"<ProductInventory(ProductID={self.ProductID}, CurrentStock={self.CurrentStock})>"


class CustomerLedger(Base):
    __tablename__ = "CustomerLedger"

    LedgerID = Column(Integer, primary_key=True, autoincrement=True)
    CustomerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    TransactionDate = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ReferenceType = Column(String(50), nullable=False)
    ReferenceID = Column(Integer, nullable=True)
    Description = Column(String(255), nullable=False)
    ProductID = Column(Integer, ForeignKey("Products.ProductID"), nullable=True)
    Quantity = Column(Float, default=0.0, nullable=False)
    Rate = Column(Float, default=0.0, nullable=False)
    Debit = Column(Float, default=0.0, nullable=False)   # Sales Invoice Amount (Receivable)
    Credit = Column(Float, default=0.0, nullable=False)  # Customer Cash Payment (Received)
    RunningBalance = Column(Float, default=0.0, nullable=False)

    customer = relationship("LabourAccount")
    product = relationship("Product")

    def __repr__(self):
        return f"<CustomerLedger(Customer='{self.CustomerID}', Debit={self.Debit}, Credit={self.Credit}, Balance={self.RunningBalance})>"


class LabourPayment(Base):
    __tablename__ = "LabourPayments"

    PaymentID = Column(Integer, primary_key=True, autoincrement=True)
    WorkerID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    PaymentDate = Column(Date, nullable=False, index=True)
    PaymentType = Column(String(50), default="Cash Payment", nullable=False)
    Amount = Column(Float, default=0.0, nullable=False)
    Remarks = Column(String(255), nullable=True)

    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    worker = relationship("LabourAccount")

    def __repr__(self):
        return f"<LabourPayment(ID={self.PaymentID}, Worker='{self.WorkerID}', Date={self.PaymentDate}, Amount={self.Amount})>"


class MoneyTransaction(Base):
    __tablename__ = "MoneyTransactions"

    TransactionID = Column(Integer, primary_key=True, autoincrement=True)
    TransactionNo = Column(String(50), unique=True, nullable=False, index=True)
    TransactionType = Column(String(20), nullable=False, index=True)  # 'RECEIPT' or 'PAYMENT'
    TransactionDate = Column(Date, nullable=False, index=True)
    AccountID = Column(String(50), ForeignKey("LabourAccounts.WorkerID", ondelete="CASCADE"), nullable=False, index=True)
    PaymentMethod = Column(String(50), default="Cash", nullable=False)
    BankAccount = Column(String(100), nullable=True)
    ChequeNumber = Column(String(100), nullable=True)
    Amount = Column(Float, default=0.0, nullable=False)
    Description = Column(String(255), nullable=False)
    ReferenceType = Column(String(50), nullable=True)
    ReferenceID = Column(String(50), nullable=True)
    IsDeleted = Column(Boolean, default=False, nullable=False, index=True)

    CreatedBy = Column(String(50), nullable=True)
    CreatedDate = Column(DateTime, default=datetime.utcnow, nullable=False)
    ModifiedBy = Column(String(50), nullable=True)
    ModifiedDate = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account = relationship("LabourAccount")

    def __repr__(self):
        return f"<MoneyTransaction(ID={self.TransactionID}, No='{self.TransactionNo}', Type='{self.TransactionType}', Account='{self.AccountID}', Amount={self.Amount})>"
