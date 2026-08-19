from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.database.schema import LabourPayment
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[LabourPayment]):
    def __init__(self, session: Session):
        super().__init__(session, LabourPayment)

    def get_by_worker(
        self,
        worker_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[LabourPayment]:
        q = (
            self.session.query(LabourPayment)
            .filter(LabourPayment.WorkerID == worker_id)
        )
        if start_date:
            q = q.filter(LabourPayment.PaymentDate >= start_date)
        if end_date:
            q = q.filter(LabourPayment.PaymentDate <= end_date)

        return q.order_by(LabourPayment.PaymentDate.asc(), LabourPayment.PaymentID.asc()).all()

    def get_payments_before_date(self, worker_id: str, before_date: date) -> List[LabourPayment]:
        return (
            self.session.query(LabourPayment)
            .filter(LabourPayment.WorkerID == worker_id)
            .filter(LabourPayment.PaymentDate < before_date)
            .all()
        )

    def add_payment(
        self,
        worker_id: str,
        payment_date: date,
        amount: float,
        payment_type: str = "Cash Payment",
        remarks: Optional[str] = None,
        created_by: str = "System"
    ) -> LabourPayment:
        payment = LabourPayment(
            WorkerID=worker_id,
            PaymentDate=payment_date,
            PaymentType=payment_type,
            Amount=amount,
            Remarks=remarks,
            CreatedBy=created_by,
            CreatedDate=datetime.utcnow(),
            ModifiedDate=datetime.utcnow()
        )
        self.session.add(payment)
        self.session.flush()
        return payment
