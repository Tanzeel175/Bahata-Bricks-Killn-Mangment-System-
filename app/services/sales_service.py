from datetime import date, datetime
from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.database.schema import LabourAccount, AccountType, Product, ProductCategory, ProductCategoryMapping
from app.repositories.sales_repository import SalesRepository
from app.repositories.labour_repository import LabourRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.audit_repository import AuditRepository
from app.security.rbac import can_delete_records
from app.security.session import current_session


class SalesService:
    """Service layer for Brick Kiln Sales Invoicing, Receipts, and Delivery Management."""

    TRANSPORT_MODES = [
        "Rehra (ریڑھا)",
        "Tractor Trolley (ٹریکٹر ٹرالی)",
        "Truck (ٹرک)",
        "Customer Own Transport (گاہک کا اپنا ٹرانسپورٹ)",
        "Mazda / Pickup (مزدا / پک اپ)",
        "Other (دیگر)"
    ]

    @classmethod
    def get_transport_modes(cls) -> List[str]:
        return cls.TRANSPORT_MODES

    @staticmethod
    def get_next_invoice_no() -> str:
        with get_db_session() as session:
            repo = SalesRepository(session)
            return repo.get_next_invoice_no()

    @staticmethod
    def get_customers() -> List[Dict[str, Any]]:
        """Fetch all active Customer accounts."""
        with get_db_session() as session:
            acc_type = session.query(AccountType).filter_by(AccountTypeName="Customer").first()
            if not acc_type:
                return []

            labour_repo = LabourRepository(session)
            customers = labour_repo.search_accounts(account_type_id=acc_type.AccountTypeID, show_omitted=False)
            return [
                {
                    "CustomerID": c.WorkerID,
                    "EnglishName": c.EnglishName,
                    "UrduName": c.UrduName or "",
                    "CNIC": c.CNIC or "",
                    "Mobile": c.Mobile or "",
                    "Address": c.Address or ""
                }
                for c in customers
            ]

    @staticmethod
    def get_sale_products() -> List[Dict[str, Any]]:
        """Fetch all products mapped to the 'Sale' category (e.g. Awal, Doam, Khinger, Tiles)."""
        with get_db_session() as session:
            cat = session.query(ProductCategory).filter_by(CategoryName="Sale").first()
            if not cat:
                # Fallback to all products if Sale category not mapped
                all_prods = session.query(Product).all()
            else:
                all_prods = (
                    session.query(Product)
                    .join(ProductCategoryMapping, Product.ProductID == ProductCategoryMapping.ProductID)
                    .filter(ProductCategoryMapping.CategoryID == cat.CategoryID)
                    .all()
                )

            return [
                {
                    "ProductID": p.ProductID,
                    "ProductName": p.ProductName,
                    "UnitRate": p.UnitRate or 0.0,
                    "StockQuantity": p.StockQuantity or 0.0
                }
                for p in all_prods
            ]

    @staticmethod
    def get_delivery_persons_by_mode(mode: str) -> List[Dict[str, Any]]:
        """
        Fetch delivery persons / drivers / rehra walas based on transport mode.
        """
        with get_db_session() as session:
            mode_lower = (mode or "").lower()
            target_types = []
            if "rehra" in mode_lower:
                target_types = ["Rehra Wala", "Transporter", "Driver", "Worker"]
            elif "tractor" in mode_lower or "truck" in mode_lower or "mazda" in mode_lower:
                target_types = ["Driver", "Transporter", "Worker"]
            else:
                target_types = ["Driver", "Transporter", "Worker", "Customer"]

            types = session.query(AccountType).filter(AccountType.AccountTypeName.in_(target_types)).all()
            type_ids = [t.AccountTypeID for t in types]

            query = session.query(LabourAccount).filter(LabourAccount.IsOmitted.is_(False))
            if type_ids:
                query = query.filter(LabourAccount.AccountTypeID.in_(type_ids))

            workers = query.all()
            return [
                {
                    "WorkerID": w.WorkerID,
                    "Name": w.EnglishName,
                    "UrduName": w.UrduName or "",
                    "Mobile": w.Mobile or "",
                    "Role": w.account_type.AccountTypeName if w.account_type else ""
                }
                for w in workers
            ]

    @staticmethod
    def save_sales_receipt(
        sale_date: date,
        customer_id: str,
        transport_mode: Optional[str],
        driver_name: Optional[str],
        vehicle_number: Optional[str],
        remarks: Optional[str],
        items_list: List[Dict[str, Any]],
        sale_id: Optional[int] = None,
        is_edit_mode: bool = False
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if not customer_id or not str(customer_id).strip():
            return False, "Customer selection is required.", None

        if not items_list or len(items_list) == 0:
            return False, "At least one product item is required on the sales receipt.", None

        for item in items_list:
            qty = float(item.get("Quantity", 0.0) or 0.0)
            rate = float(item.get("RatePer1000", 0.0) or 0.0)
            if qty <= 0:
                return False, f"Quantity must be greater than 0 for all items.", None
            if rate <= 0:
                return False, f"Rate per 1,000 must be greater than 0 for all items.", None

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                repo = SalesRepository(session)
                audit_repo = AuditRepository(session)
                labour_repo = LabourRepository(session)

                cust = labour_repo.get_by_worker_id(customer_id)
                cust_name = cust.EnglishName if cust else customer_id

                header = repo.save_sale(
                    sale_date=sale_date,
                    customer_id=customer_id,
                    transport_mode=transport_mode,
                    driver_name=driver_name,
                    vehicle_number=vehicle_number,
                    remarks=remarks,
                    items_list=items_list,
                    sale_id=sale_id,
                    user_name=user_name
                )

                action = "SALE_UPDATE" if is_edit_mode else "SALE_CREATE"
                audit_repo.log_event(
                    action=action,
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"{action}: Invoice={header.InvoiceNo}, Customer={cust_name}, Amount=Rs.{header.TotalAmount:,.2f}, Items={len(items_list)}"
                )
                session.commit()

                res_dict = {
                    "SaleID": header.SaleID,
                    "InvoiceNo": header.InvoiceNo,
                    "SaleDate": header.SaleDate.strftime("%Y-%m-%d"),
                    "CustomerID": header.CustomerID,
                    "CustomerName": cust_name,
                    "TransportMode": header.TransportMode or "",
                    "DriverName": header.DriverName or "",
                    "VehicleNumber": header.VehicleNumber or "",
                    "Remarks": header.Remarks or "",
                    "TotalAmount": header.TotalAmount
                }
                return True, f"Sales Receipt '{header.InvoiceNo}' saved successfully! Amount: Rs. {header.TotalAmount:,.2f}", res_dict
        except Exception as e:
            return False, f"Failed to save sales receipt: {str(e)}", None

    @staticmethod
    def get_sale_by_id(sale_id: int) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            repo = SalesRepository(session)
            s = repo.get_by_id(sale_id)
            if not s:
                return None

            items = []
            for d in s.details:
                items.append({
                    "SaleDetailID": d.SaleDetailID,
                    "ProductID": d.ProductID,
                    "ProductName": d.product.ProductName if d.product else f"Product #{d.ProductID}",
                    "Quantity": d.Quantity,
                    "RatePer1000": d.RatePer1000,
                    "TotalAmount": d.TotalAmount
                })

            return {
                "SaleID": s.SaleID,
                "InvoiceNo": s.InvoiceNo,
                "SaleDate": s.SaleDate.strftime("%Y-%m-%d"),
                "CustomerID": s.CustomerID,
                "CustomerName": s.customer.EnglishName if s.customer else s.CustomerID,
                "CustomerUrdu": s.customer.UrduName if s.customer else "",
                "CustomerMobile": s.customer.Mobile if s.customer else "",
                "TransportMode": s.TransportMode or "",
                "DriverName": s.DriverName or "",
                "VehicleNumber": s.VehicleNumber or "",
                "Remarks": s.Remarks or "",
                "TotalAmount": s.TotalAmount,
                "CreatedBy": s.CreatedBy or "",
                "CreatedDate": s.CreatedDate.strftime("%Y-%m-%d %H:%M") if s.CreatedDate else "",
                "Details": items
            }

    @staticmethod
    def search_sales(
        customer_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        search_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = SalesRepository(session)
            sales = repo.search_sales(customer_id, from_date, to_date, search_text)
            result = []
            for s in sales:
                item_descs = [f"{d.product.ProductName if d.product else 'Item'} ({d.Quantity:,.0f})" for d in s.details]
                summary_str = ", ".join(item_descs)
                result.append({
                    "SaleID": s.SaleID,
                    "InvoiceNo": s.InvoiceNo,
                    "SaleDate": s.SaleDate.strftime("%Y-%m-%d"),
                    "CustomerID": s.CustomerID,
                    "CustomerName": s.customer.EnglishName if s.customer else s.CustomerID,
                    "TransportMode": s.TransportMode or "",
                    "DriverName": s.DriverName or "",
                    "VehicleNumber": s.VehicleNumber or "",
                    "TotalAmount": s.TotalAmount,
                    "ItemsCount": len(s.details),
                    "ItemsSummary": summary_str,
                    "Remarks": s.Remarks or "",
                    "CreatedBy": s.CreatedBy or ""
                })
            return result

    @staticmethod
    def delete_sales_receipt(sale_id: int) -> Tuple[bool, str]:
        if not can_delete_records():
            return False, "Access Denied: Only System Administrators can delete sales receipts."

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                repo = SalesRepository(session)
                audit_repo = AuditRepository(session)

                sale = repo.get_by_id(sale_id)
                if not sale:
                    return False, f"Sales Receipt #{sale_id} not found."

                inv_no = sale.InvoiceNo
                cust_name = sale.customer.EnglishName if sale.customer else sale.CustomerID
                total_amt = sale.TotalAmount

                succ = repo.delete_sale(sale_id)
                if succ:
                    audit_repo.log_event(
                        action="SALE_DELETE",
                        username=user_name,
                        user_id=current_session.user_id,
                        details=f"SALE_DELETE: Reverted Receipt={inv_no}, Customer={cust_name}, Amount=Rs.{total_amt:,.2f}"
                    )
                    session.commit()
                    return True, f"Sales Receipt '{inv_no}' deleted and reversed successfully."
                else:
                    return False, "Failed to delete sales receipt."
        except Exception as e:
            return False, f"Error deleting sales receipt: {str(e)}"
