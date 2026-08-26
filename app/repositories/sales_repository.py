from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database.schema import SalesHeader, SalesDetail, LabourAccount, Product
from app.repositories.base_repository import BaseRepository


class SalesRepository(BaseRepository[SalesHeader]):
    """Data Access Layer for Brick Kiln Sales Receipts and Invoicing."""

    def __init__(self, session: Session):
        super().__init__(session, SalesHeader)

    def get_next_invoice_no(self) -> str:
        """Generates the next sequential invoice number like SAL-0001."""
        max_id = self.session.query(func.max(SalesHeader.SaleID)).scalar() or 0
        return f"SAL-{max_id + 1:04d}"

    def get_by_id(self, sale_id: int) -> Optional[SalesHeader]:
        return (
            self.session.query(SalesHeader)
            .options(
                joinedload(SalesHeader.customer),
                joinedload(SalesHeader.details).joinedload(SalesDetail.product)
            )
            .filter(SalesHeader.SaleID == sale_id)
            .first()
        )

    def get_by_invoice_no(self, invoice_no: str) -> Optional[SalesHeader]:
        return (
            self.session.query(SalesHeader)
            .options(
                joinedload(SalesHeader.customer),
                joinedload(SalesHeader.details).joinedload(SalesDetail.product)
            )
            .filter(SalesHeader.InvoiceNo == invoice_no)
            .first()
        )

    def save_sale(
        self,
        sale_date: date,
        customer_id: str,
        transport_mode: Optional[str],
        driver_name: Optional[str],
        vehicle_number: Optional[str],
        remarks: Optional[str],
        items_list: List[Dict[str, Any]],
        sale_id: Optional[int] = None,
        user_name: str = "System"
    ) -> SalesHeader:
        """
        Saves a sales receipt header and its multi-product line items atomically.
        """
        total_amount = 0.0

        if sale_id:
            header = self.get_by_id(sale_id)
            if not header:
                raise ValueError(f"Sales Receipt with ID {sale_id} not found.")

            header.SaleDate = sale_date
            header.CustomerID = customer_id
            header.TransportMode = transport_mode
            header.DriverName = driver_name
            header.VehicleNumber = vehicle_number
            header.Remarks = remarks
            header.ModifiedBy = user_name
            header.ModifiedDate = datetime.utcnow()

            # Clear existing details
            self.session.query(SalesDetail).filter_by(SaleID=sale_id).delete()
        else:
            invoice_no = self.get_next_invoice_no()
            header = SalesHeader(
                InvoiceNo=invoice_no,
                SaleDate=sale_date,
                CustomerID=customer_id,
                TransportMode=transport_mode,
                DriverName=driver_name,
                VehicleNumber=vehicle_number,
                Remarks=remarks,
                TotalAmount=0.0,
                CreatedBy=user_name,
                CreatedDate=datetime.utcnow(),
                ModifiedBy=user_name,
                ModifiedDate=datetime.utcnow()
            )
            self.session.add(header)
            self.session.flush()

        # Add line items
        for item in items_list:
            qty = float(item.get("Quantity", 0.0) or 0.0)
            rate = float(item.get("RatePer1000", 0.0) or 0.0)
            line_total = (qty / 1000.0) * rate
            total_amount += line_total

            detail = SalesDetail(
                SaleID=header.SaleID,
                ProductID=int(item["ProductID"]),
                Quantity=qty,
                RatePer1000=rate,
                TotalAmount=line_total
            )
            self.session.add(detail)

        header.TotalAmount = total_amount
        self.session.flush()
        return header

    def search_sales(
        self,
        customer_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        search_text: Optional[str] = None
    ) -> List[SalesHeader]:
        query = (
            self.session.query(SalesHeader)
            .options(
                joinedload(SalesHeader.customer),
                joinedload(SalesHeader.details).joinedload(SalesDetail.product)
            )
            .join(LabourAccount, SalesHeader.CustomerID == LabourAccount.WorkerID)
        )

        if customer_id:
            query = query.filter(SalesHeader.CustomerID == customer_id)

        if from_date:
            query = query.filter(SalesHeader.SaleDate >= from_date)

        if to_date:
            query = query.filter(SalesHeader.SaleDate <= to_date)

        if search_text:
            pattern = f"%{search_text.strip()}%"
            query = query.filter(
                (SalesHeader.InvoiceNo.ilike(pattern)) |
                (LabourAccount.EnglishName.ilike(pattern)) |
                (SalesHeader.DriverName.ilike(pattern)) |
                (SalesHeader.VehicleNumber.ilike(pattern)) |
                (SalesHeader.Remarks.ilike(pattern))
            )

        return query.order_by(SalesHeader.SaleDate.desc(), SalesHeader.SaleID.desc()).all()

    def delete_sale(self, sale_id: int) -> bool:
        header = self.get_by_id(sale_id)
        if not header:
            return False
        self.session.delete(header)
        self.session.flush()
        return True
