from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.database.schema import LabourRate, LabourAccount, Product
from app.repositories.base_repository import BaseRepository


class RateRepository(BaseRepository[LabourRate]):
    def __init__(self, session: Session):
        super().__init__(session, LabourRate)

    def get_rate(self, worker_id: str, product_id: int) -> float:
        rate_entry = (
            self.session.query(LabourRate)
            .filter(LabourRate.WorkerID == worker_id, LabourRate.ProductID == product_id)
            .order_by(LabourRate.EffectiveDate.desc())
            .first()
        )
        return rate_entry.RatePer1000 if rate_entry else 0.0

    def get_worker_rates(self, worker_id: str) -> Dict[int, float]:
        rates = (
            self.session.query(LabourRate)
            .filter(LabourRate.WorkerID == worker_id)
            .all()
        )
        return {r.ProductID: r.RatePer1000 for r in rates}

    def save_worker_rates(self, worker_id: str, rate_dict: Dict[int, float], user_name: str = "System"):
        for product_id, rate_val in rate_dict.items():
            rate_entry = (
                self.session.query(LabourRate)
                .filter(LabourRate.WorkerID == worker_id, LabourRate.ProductID == product_id)
                .first()
            )
            if rate_entry:
                rate_entry.RatePer1000 = rate_val
                rate_entry.ModifiedBy = user_name
                rate_entry.ModifiedDate = datetime.utcnow()
            else:
                rate_entry = LabourRate(
                    WorkerID=worker_id,
                    ProductID=product_id,
                    RatePer1000=rate_val,
                    CreatedBy=user_name,
                    CreatedDate=datetime.utcnow(),
                    ModifiedBy=user_name,
                    ModifiedDate=datetime.utcnow()
                )
                self.session.add(rate_entry)
        self.session.flush()
