from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from app.config import COMPANY_NAME, APP_SUBTITLE
from app.database.connection import get_db_session
from app.database.schema import (
    LabourAccount, AccountType, ProductionDetail, ProductionHeader, Product,
    LabourRate, SalesHeader, SalesDetail, LabourPayment, MoneyTransaction
)
from app.repositories.labour_repository import LabourRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.audit_repository import AuditRepository
from app.security.session import current_session


class LedgerService:
    """
    Unified Calculated Ledger Engine.
    Dynamically computes opening balance, period transactions, running balance,
    totals, and closing balance statements across Labour Production, Customer Sales,
    and unified Money Transactions (Amdan & Akrajat).
    """

    SUPPORTED_CATEGORIES = [
        "Customer", "Pathera", "Bahri Wala", "Nakkasi Wala", "Jamadar",
        "Pathera Jamadar", "Nakkasi Jamadar", "Purchase Party", "Owner",
        "Transporter", "Driver", "Worker", "Salesman", "Mutfariq Expenses",
        "Mutfariq Income", "Cashier", "Fixed Assets", "Others"
    ]

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
            is_customer = (account_type_name == "Customer")

            all_txns = []

            if is_customer:
                # 1. Fetch Sales Details for this Customer
                sales_details = (
                    session.query(SalesDetail)
                    .join(SalesHeader, SalesDetail.SaleID == SalesHeader.SaleID)
                    .join(Product, SalesDetail.ProductID == Product.ProductID)
                    .filter(SalesHeader.CustomerID == worker_id)
                    .all()
                )

                for d in sales_details:
                    s_date = d.header.SaleDate
                    prod_name = d.product.ProductName if d.product else f"Product #{d.ProductID}"
                    t_mode = d.header.TransportMode or ""
                    d_name = d.header.DriverName or ""
                    trans_str = ""
                    if t_mode:
                        trans_str = f" via {t_mode}"
                    if d_name:
                        trans_str += f" ({d_name})"

                    desc = f"{prod_name} ({d.Quantity:,.0f} @ Rs. {d.RatePer1000:,.2f}/1000){trans_str}"

                    all_txns.append({
                        "date": s_date,
                        "type": "SALE",
                        "ref": d.header.InvoiceNo,
                        "description": desc,
                        "debit": d.TotalAmount,  # Receivable from customer
                        "credit": 0.0,
                        "raw_id": d.SaleID
                    })

                # 2. Fetch MoneyTransactions (Amdan & Akrajat) for this Customer
                txn_repo = TransactionRepository(session)
                money_txns = txn_repo.get_by_account(worker_id, include_deleted=False)
                seen_payment_ids = set()

                for mt in money_txns:
                    if mt.ReferenceType == "LabourPayment" and mt.ReferenceID and mt.ReferenceID.isdigit():
                        seen_payment_ids.add(int(mt.ReferenceID))

                    if mt.TransactionType == "RECEIPT":
                        # Amdan: Customer deposited cash/bank payment -> Credit to Customer
                        desc = f"Amdan / Receipt (آمدن): {mt.PaymentMethod}"
                        if mt.Description:
                            desc += f" - {mt.Description}"
                        all_txns.append({
                            "date": mt.TransactionDate,
                            "type": "RECEIPT",
                            "ref": mt.TransactionNo,
                            "description": desc,
                            "credit": mt.Amount,
                            "debit": 0.0,
                            "raw_id": mt.TransactionID
                        })
                    else:
                        # Akrajat: Customer refund or return payment -> Debit to Customer
                        desc = f"Akrajat / Payment (اخراجات): {mt.PaymentMethod}"
                        if mt.Description:
                            desc += f" - {mt.Description}"
                        all_txns.append({
                            "date": mt.TransactionDate,
                            "type": "PAYMENT",
                            "ref": mt.TransactionNo,
                            "description": desc,
                            "credit": 0.0,
                            "debit": mt.Amount,
                            "raw_id": mt.TransactionID
                        })

                # 3. Fetch legacy Payments received from Customer (excluding already migrated/synced)
                payment_repo = PaymentRepository(session)
                payments = payment_repo.get_by_worker(worker_id)

                for p in payments:
                    if p.PaymentID in seen_payment_ids:
                        continue
                    desc = f"Payment Received: {p.PaymentType}"
                    if p.Remarks and p.Remarks.strip():
                        desc += f" - {p.Remarks.strip()}"

                    all_txns.append({
                        "date": p.PaymentDate,
                        "type": "PAYMENT",
                        "ref": f"PAY-{p.PaymentID:04d}",
                        "description": desc,
                        "credit": p.Amount,  # Customer paid money
                        "debit": 0.0,
                        "raw_id": p.PaymentID
                    })

                # Customer Opening Balance: Credits (Payments) - Debits (Sales)
                prior_txns = [t for t in all_txns if t["date"] < from_date]
                opening_credit = sum(t["credit"] for t in prior_txns)
                opening_debit = sum(t["debit"] for t in prior_txns)
                opening_balance = opening_credit - opening_debit

                # Period Transactions
                period_txns = [t for t in all_txns if from_date <= t["date"] <= to_date]
                period_txns.sort(key=lambda x: (x["date"], 0 if x["type"] == "SALE" else 1, x["ref"]))

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

                if closing_balance < 0:
                    statement_label = f"AMOUNT RECEIVABLE FROM CUSTOMER (BAQI): -Rs. {abs(closing_balance):,.2f}"
                    statement_status = "RECEIVABLE"
                elif closing_balance > 0:
                    statement_label = f"ADVANCE MONEY RECEIVED FROM CUSTOMER: Rs. {closing_balance:,.2f}"
                    statement_status = "ADVANCE"
                else:
                    statement_label = "NIL / ZERO BALANCE: Rs. 0.00"
                    statement_status = "BALANCED"

            else:
                # --- LABOURER LEDGER LOGIC ---
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

                # 2. Fetch MoneyTransactions (Amdan & Akrajat) for this worker
                txn_repo = TransactionRepository(session)
                money_txns = txn_repo.get_by_account(worker_id, include_deleted=False)
                seen_payment_ids = set()

                for mt in money_txns:
                    if mt.ReferenceType == "LabourPayment" and mt.ReferenceID and mt.ReferenceID.isdigit():
                        seen_payment_ids.add(int(mt.ReferenceID))

                    if mt.TransactionType == "PAYMENT":
                        # Akrajat: Payment or advance given to worker -> Debit (increases advance / drawings)
                        desc = f"Akrajat / Payment (اخراجات): {mt.PaymentMethod}"
                        if mt.Description:
                            desc += f" - {mt.Description}"
                        all_txns.append({
                            "date": mt.TransactionDate,
                            "type": "PAYMENT",
                            "ref": mt.TransactionNo,
                            "description": desc,
                            "credit": 0.0,
                            "debit": mt.Amount,
                            "raw_id": mt.TransactionID
                        })
                    else:
                        # Amdan: Worker returned advance or repaid debt -> Credit (reduces debt)
                        desc = f"Amdan / Receipt (آمدن): {mt.PaymentMethod}"
                        if mt.Description:
                            desc += f" - {mt.Description}"
                        all_txns.append({
                            "date": mt.TransactionDate,
                            "type": "RECEIPT",
                            "ref": mt.TransactionNo,
                            "description": desc,
                            "credit": mt.Amount,
                            "debit": 0.0,
                            "raw_id": mt.TransactionID
                        })

                # 3. Fetch legacy Payment Transactions for this worker (excluding synced)
                payment_repo = PaymentRepository(session)
                payments = payment_repo.get_by_worker(worker_id)

                for p in payments:
                    if p.PaymentID in seen_payment_ids:
                        continue
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
                worker = session.query(LabourAccount).filter_by(WorkerID=worker_id).first()
                is_customer = False
                if worker and worker.account_type and worker.account_type.AccountTypeName == "Customer":
                    is_customer = True

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

                # Synchronize to unified MoneyTransactions table
                txn_repo = TransactionRepository(session)
                txn_type = "RECEIPT" if is_customer else "PAYMENT"
                txn_no = txn_repo.get_next_transaction_no(txn_type)
                method_name = "Cash" if "cash" in (payment_type or "").lower() else "Bank"
                desc = remarks or (f"Customer payment: {payment_type}" if is_customer else f"Labour payment: {payment_type}")
                txn_repo.create_transaction(
                    txn_no=txn_no,
                    txn_type=txn_type,
                    txn_date=payment_date,
                    account_id=worker_id,
                    amount=amount,
                    description=desc,
                    payment_method=method_name,
                    reference_type="LabourPayment",
                    reference_id=str(payment.PaymentID),
                    user_name=user_name
                )

                audit_repo.log_event(
                    action="PAYMENT_CREATE" if not is_customer else "RECEIPT_CREATE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"PAYMENT_RECORD: PaymentID={payment.PaymentID}, TransactionNo={txn_no}, AccountID='{worker_id}', Amount={amount:,.2f}"
                )

                session.commit()
                entity_label = "Customer" if is_customer else "Worker"
                return True, f"Payment of Rs. {amount:,.2f} recorded successfully for {entity_label} {worker_id}."
        except Exception as e:
            return False, f"Failed to record payment: {e}"
