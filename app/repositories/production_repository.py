from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import or_
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.database.schema import (
    ProductionHeader, ProductionDetail, LabourAccount, Product, AccountType
)
from app.repositories.base_repository import BaseRepository
from app.repositories.rate_repository import RateRepository


class ProductionRepository(BaseRepository[ProductionHeader]):
    def __init__(self, session: Session):
        super().__init__(session, ProductionHeader)

    def get_by_id(self, production_id: int) -> Optional[ProductionHeader]:
        return (
            self.session.query(ProductionHeader)
            .options(
                joinedload(ProductionHeader.account_type),
                joinedload(ProductionHeader.details).joinedload(ProductionDetail.worker),
                joinedload(ProductionHeader.details).joinedload(ProductionDetail.product)
            )
            .filter(ProductionHeader.ProductionID == production_id)
            .first()
        )

    def get_by_date_and_category(self, entry_date: date, account_type_id: int) -> Optional[ProductionHeader]:
        return (
            self.session.query(ProductionHeader)
            .options(
                joinedload(ProductionHeader.account_type),
                joinedload(ProductionHeader.details).joinedload(ProductionDetail.worker),
                joinedload(ProductionHeader.details).joinedload(ProductionDetail.product)
            )
            .filter(ProductionHeader.EntryDate == entry_date, ProductionHeader.AccountTypeID == account_type_id)
            .first()
        )

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        headers = (
            self.session.query(ProductionHeader)
            .options(
                joinedload(ProductionHeader.account_type),
                joinedload(ProductionHeader.details)
            )
            .order_by(ProductionHeader.EntryDate.desc(), ProductionHeader.ProductionID.desc())
            .limit(limit)
            .all()
        )

        result = []
        for h in headers:
            total_qty = sum(d.Quantity for d in h.details)
            worker_count = len({d.WorkerID for d in h.details})
            result.append({
                "ProductionID": h.ProductionID,
                "EntryDate": h.EntryDate.strftime("%Y-%m-%d"),
                "AccountTypeID": h.AccountTypeID,
                "AccountTypeName": h.account_type.AccountTypeName if h.account_type else "Unknown",
                "CategoryName": h.account_type.AccountTypeName if h.account_type else "Unknown",
                "TotalQuantity": total_qty,
                "WorkerCount": worker_count,
                "Remarks": h.Remarks or "",
                "CreatedBy": h.CreatedBy or "System",
                "CreatedDate": h.CreatedDate.strftime("%Y-%m-%d %H:%M") if h.CreatedDate else ""
            })
        return result

    def search_production_entries(
        self,
        account_type_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[ProductionHeader]:
        q = (
            self.session.query(ProductionHeader)
            .options(joinedload(ProductionHeader.account_type))
        )

        if account_type_id and account_type_id > 0:
            q = q.filter(ProductionHeader.AccountTypeID == account_type_id)

        if start_date:
            q = q.filter(ProductionHeader.EntryDate >= start_date)
        if end_date:
            q = q.filter(ProductionHeader.EntryDate <= end_date)

        return q.order_by(ProductionHeader.EntryDate.desc(), ProductionHeader.ProductionID.desc()).all()

    def save_production_entry(
        self,
        entry_date: date,
        account_type_id: int,
        details_list: List[Dict[str, Any]],
        remarks: Optional[str] = None,
        production_id: Optional[int] = None,
        user_name: str = "System"
    ) -> ProductionHeader:
        if production_id and int(production_id) > 0:
            header = self.get_by_id(int(production_id))
            if not header:
                raise ValueError(f"Production Entry ID {production_id} not found.")

            header.EntryDate = entry_date
            header.AccountTypeID = account_type_id
            header.Remarks = remarks or None
            header.ModifiedBy = user_name
            header.ModifiedDate = datetime.utcnow()

            # Delete old details
            self.session.query(ProductionDetail).filter(ProductionDetail.ProductionID == header.ProductionID).delete()
        else:
            header = ProductionHeader(
                EntryDate=entry_date,
                AccountTypeID=account_type_id,
                Remarks=remarks or None,
                CreatedBy=user_name,
                CreatedDate=datetime.utcnow(),
                ModifiedBy=user_name,
                ModifiedDate=datetime.utcnow()
            )
            self.session.add(header)
            self.session.flush()

        for d in details_list:
            worker_id = str(d["WorkerID"]).strip()
            product_id = int(d["ProductID"])
            qty = float(d.get("Quantity", 0.0) or 0.0)

            if qty <= 0.0:
                continue

            detail = ProductionDetail(
                ProductionID=header.ProductionID,
                WorkerID=worker_id,
                ProductID=product_id,
                Quantity=qty
            )
            self.session.add(detail)

        self.session.flush()
        return header

    def delete_production_entry(self, production_id: int) -> bool:
        header = self.get_by_id(production_id)
        if not header:
            return False

        # Delete header (cascade deletes details)
        self.session.delete(header)
        self.session.flush()
        return True
