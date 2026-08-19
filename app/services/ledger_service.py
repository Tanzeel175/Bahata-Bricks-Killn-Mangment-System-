from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from app.config import COMPANY_NAME, APP_SUBTITLE
from app.database.connection import get_db_session
from app.database.schema import LabourAccount, AccountType, ProductionDetail, ProductionHeader, Product, LabourRate
from app.repositories.labour_repository import LabourRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.audit_repository import AuditRepository
from app.security.session import current_session


class LedgerService:
    """
    Unified Calculated Ledger Engine.
    Dynamically computes opening balance, period transactions, running balance,
    totals, and closing balance statements across Production and Payments.
    """

    SUPPORTED_CATEGORIES = ["Pathera", "Bahri Wala", "Nakkasi Wala"]

    @classmethod
    def get_supported_categories(cls) -> List[str]:
        return cls.SUPPORTED_CATEGORIES

    @staticmethod
    def get_workers_by_category(category_name: str) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            account_type = session.query(AccountType).filter_by(AccountTypeName=category_name).first()
            if not account_type:
                return []

            labour_repo = LabourRepository(session)
            workers = labour_repo.search_accounts(account_type_id=account_type.AccountTypeID, show_omitted=False)
            return [
                {
                    "WorkerID": w.WorkerID,
                    "EnglishName": w.EnglishName,
                    "UrduName": w.UrduName or "",
                    "CNIC": w.CNIC or "",
                    "Mobile": w.Mobile or "",
                    "AccountTypeName": category_name
                }
                for w in workers
            ]

    @staticmethod
    def calculate_worker_ledger(
        worker_id: str,
        from_date: date,
        to_date: date
    ) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            worker = session.query(LabourAccount).filter_by(WorkerID=worker_id).first()
            if not worker:
                return None

            account_type_name = worker.account_type.AccountTypeName if worker.account_type else "Unknown"

            # 1. Fetch Production Detail Transactions for this worker
            details = (
                session.query(ProductionDetail)
                .join(ProductionHeader, ProductionDetail.ProductionID == ProductionHeader.ProductionID)
                .join(Product, ProductionDetail.ProductID == Product.ProductID)
                .filter(ProductionDetail.WorkerID == worker_id)
                .all()
            )

            # Pre-cache worker rates
            rates_query = session.query(LabourRate).filter_by(WorkerID=worker_id).all()
            rates_map = {r.ProductID: r.RatePer1000 for r in rates_query}

            all_txns = []

            for d in details:
                p_date = d.header.EntryDate
                rate = rates_map.get(d.ProductID, d.product.UnitRate or 0.0)
                credit = (d.Quantity / 1000.0) * rate
                prod_name = d.product.ProductName if d.product else f"Product #{d.ProductID}"
                display_prod = prod_name
                if display_prod in ["Awal", "Doam", "Khinger"]:
                    display_prod = f"{display_prod} Bricks"

                all_txns.append({
                    "date": p_date,
                    "type": "PRODUCTION",
                    "ref": f"PRD-{d.ProductionID:04d}",
                    "description": f"{display_prod} ({d.Quantity:,.0f} @ Rs. {rate:,.2f}/1000)",
                    "credit": credit,
                    "debit": 0.0,
                    "raw_id": d.ProductionID
                })

            # 2. Fetch Payment Transactions for this worker
            payment_repo = PaymentRepository(session)
            payments = payment_repo.get_by_worker(worker_id)

            for p in payments:
                desc = p.PaymentType
                if p.Remarks and p.Remarks.strip():
                    desc += f" - {p.Remarks.strip()}"

                all_txns.append({
                    "date": p.PaymentDate,
                    "type": "PAYMENT",
                    "ref": f"PAY-{p.PaymentID:04d}",
                    "description": desc,
                    "credit": 0.0,
                    "debit": p.Amount,
                    "raw_id": p.PaymentID
                })

            # 3. Calculate Opening Balance (Transactions prior to from_date)
            prior_txns = [t for t in all_txns if t["date"] < from_date]
            opening_credit = sum(t["credit"] for t in prior_txns)
            opening_debit = sum(t["debit"] for t in prior_txns)
            opening_balance = opening_credit - opening_debit

            # 4. Period Transactions (from_date <= date <= to_date)
            period_txns = [t for t in all_txns if from_date <= t["date"] <= to_date]
            period_txns.sort(key=lambda x: (x["date"], 0 if x["type"] == "PRODUCTION" else 1, x["ref"]))

            current_running = opening_balance
            processed_period_txns = []

            total_credit = 0.0
            total_debit = 0.0

            for t in period_txns:
                credit = t["credit"]
                debit = t["debit"]
                current_running += (credit - debit)
                total_credit += credit
                total_debit += debit

                processed_period_txns.append({
                    "date_str": t["date"].strftime("%d-%b-%Y"),
                    "ref": t["ref"],
                    "description": t["description"],
                    "credit": credit,
                    "debit": debit,
                    "running_balance": current_running,
                    "raw_id": t["raw_id"],
                    "type": t["type"]
                })

            closing_balance = opening_balance + total_credit - total_debit

            if closing_balance > 0:
                statement_label = f"AMOUNT PAYABLE TO LABOUR: Rs. {closing_balance:,.2f}"
                statement_status = "PAYABLE"
            elif closing_balance < 0:
                statement_label = f"ADVANCE / DEBIT BALANCE: Rs. {abs(closing_balance):,.2f}"
                statement_status = "ADVANCE"
            else:
                statement_label = "NIL / ZERO BALANCE: Rs. 0.00"
                statement_status = "BALANCED"

            # Retrieve owner contact details from current user session or defaults
            company_info = {
                "name": COMPANY_NAME,
                "subtitle": APP_SUBTITLE,
                "owner": "Haji Abdul Rehman",
                "mobile": "0300-1234567"
            }

            worker_info = {
                "worker_id": worker.WorkerID,
                "english_name": worker.EnglishName,
                "urdu_name": worker.UrduName or "",
                "cnic": worker.CNIC or "",
                "mobile": worker.Mobile or "",
                "category": account_type_name
            }

            return {
                "company": company_info,
                "worker": worker_info,
                "period": {
                    "from_date": from_date.strftime("%d-%b-%Y"),
                    "to_date": to_date.strftime("%d-%b-%Y"),
                    "raw_from": from_date,
                    "raw_to": to_date
                },
                "opening_balance": opening_balance,
                "transactions": processed_period_txns,
                "total_credit": total_credit,
                "total_debit": total_debit,
                "closing_balance": closing_balance,
                "statement_label": statement_label,
                "statement_status": statement_status
            }

    @staticmethod
    def save_labour_payment(
        worker_id: str,
        payment_date: date,
        amount: float,
        payment_type: str = "Cash Payment",
        remarks: Optional[str] = None
    ) -> Tuple[bool, str]:
        if not worker_id:
            return False, "Labourer selection is mandatory."
        if amount <= 0:
            return False, "Payment amount must be greater than zero."

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                payment_repo = PaymentRepository(session)
                audit_repo = AuditRepository(session)

                payment = payment_repo.add_payment(
                    worker_id=worker_id,
                    payment_date=payment_date,
                    amount=amount,
                    payment_type=payment_type,
                    remarks=remarks,
                    created_by=user_name
                )

                audit_repo.log_event(
                    action="PAYMENT_CREATE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"PAYMENT_CREATE: PaymentID={payment.PaymentID}, WorkerID='{worker_id}', Amount={amount:,.2f}"
                )

                session.commit()
                return True, f"Payment of Rs. {amount:,.2f} recorded successfully for Worker {worker_id}."
        except Exception as e:
            return False, f"Failed to record payment: {e}"
