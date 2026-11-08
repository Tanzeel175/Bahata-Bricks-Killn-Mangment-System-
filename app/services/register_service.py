from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload

from app.database.connection import get_db_session
from app.database.schema import (
    LabourAccount, AccountType, Product, ProductionHeader, ProductionDetail,
    LabourRate, SalesHeader, SalesDetail, LabourPayment, MoneyTransaction
)
from app.repositories.labour_repository import LabourRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.ledger_service import LedgerService


class RegisterService:
    """
    Centralized Query & Aggregation Engine for All Business Registers & Khatas.
    Supports:
    1. All-Customers Date-to-Date Summary Register
    2. Labour Category (Pathera, Bahri Wala, Nakkasi, Jamadar, etc.) & All-Labour Summary Register
    3. Detailed Sales Invoicing Register
    4. Daily Production & Work Register
    5. Unified Amdan & Akrajat (Cashbook / Receipts & Expenses) Register
    6. General Account Category Summary (Purchase Party, Transporters, Owners, etc.)
    """

    @staticmethod
    def get_supported_categories() -> List[str]:
        return LedgerService.get_supported_categories()

    @staticmethod
    def get_labour_categories() -> List[str]:
        return [
            "Pathera", "Bahri Wala", "Nakkasi Wala", "Jamadar",
            "Pathera Jamadar", "Nakkasi Jamadar", "Worker"
        ]

    @staticmethod
    def get_other_categories() -> List[str]:
        return [
            "Purchase Party", "Owner", "Transporter", "Driver",
            "Salesman", "Mutfariq Expenses", "Mutfariq Income",
            "Cashier", "Fixed Assets", "Others"
        ]

    # =========================================================================
    # 1. CUSTOMERS REGISTER & SUMMARY (DATE TO DATE)
    # =========================================================================
    @staticmethod
    def get_customers_summary_report(
        from_date: date,
        to_date: date,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate ledger performance across ALL Customers for a given date range.
        Returns:
            - customer_rows: list of dicts with opening_balance, period_sales, period_receipts, closing_balance, status.
            - kpis: total_customers, total_sales, total_receipts, total_receivable_baqi, total_advance.
        """
        with get_db_session() as session:
            acc_type = session.query(AccountType).filter_by(AccountTypeName="Customer").first()
            if not acc_type:
                return {"rows": [], "kpis": {}}

            query = session.query(LabourAccount).filter(
                LabourAccount.AccountTypeID == acc_type.AccountTypeID,
                LabourAccount.IsOmitted.is_(False)
            )

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        LabourAccount.WorkerID.ilike(s),
                        LabourAccount.EnglishName.ilike(s),
                        LabourAccount.UrduName.ilike(s),
                        LabourAccount.Mobile.ilike(s)
                    )
                )

            customers = query.order_by(LabourAccount.EnglishName.asc()).all()
            customer_ids = [c.WorkerID for c in customers]

            if not customer_ids:
                return {
                    "rows": [],
                    "kpis": {
                        "total_customers": 0,
                        "total_sales": 0.0,
                        "total_receipts": 0.0,
                        "total_baqi": 0.0,
                        "total_advance": 0.0,
                        "net_receivable": 0.0
                    }
                }

            # Pre-fetch all sales details for these customers
            sales_headers = (
                session.query(SalesHeader)
                .filter(SalesHeader.CustomerID.in_(customer_ids))
                .options(joinedload(SalesHeader.details))
                .all()
            )
            # Map: customer_id -> list of sales
            sales_map: Dict[str, List[SalesHeader]] = {cid: [] for cid in customer_ids}
            for sh in sales_headers:
                if sh.CustomerID in sales_map:
                    sales_map[sh.CustomerID].append(sh)

            # Pre-fetch all money transactions for these customers
            money_txns = (
                session.query(MoneyTransaction)
                .filter(
                    MoneyTransaction.AccountID.in_(customer_ids),
                    MoneyTransaction.IsDeleted.is_(False)
                )
                .all()
            )
            money_map: Dict[str, List[MoneyTransaction]] = {cid: [] for cid in customer_ids}
            for mt in money_txns:
                if mt.AccountID in money_map:
                    money_map[mt.AccountID].append(mt)

            # Pre-fetch legacy payments
            legacy_payments = (
                session.query(LabourPayment)
                .filter(LabourPayment.WorkerID.in_(customer_ids))
                .all()
            )
            payment_map: Dict[str, List[LabourPayment]] = {cid: [] for cid in customer_ids}
            for lp in legacy_payments:
                if lp.WorkerID in payment_map:
                    payment_map[lp.WorkerID].append(lp)

            rows = []
            grand_sales = 0.0
            grand_receipts = 0.0
            grand_baqi = 0.0
            grand_advance = 0.0

            for c in customers:
                cid = c.WorkerID
                c_sales = sales_map.get(cid, [])
                c_money = money_map.get(cid, [])
                c_payments = payment_map.get(cid, [])

                # Track seen payment IDs to avoid duplicate counting with synced MoneyTransactions
                seen_payment_ids = set()
                for mt in c_money:
                    if mt.ReferenceType == "LabourPayment" and mt.ReferenceID and mt.ReferenceID.isdigit():
                        seen_payment_ids.add(int(mt.ReferenceID))

                # Compute prior to from_date
                prior_sales = sum(s.TotalAmount for s in c_sales if s.SaleDate < from_date)
                prior_receipts = 0.0
                for mt in c_money:
                    if mt.TransactionDate < from_date:
                        if mt.TransactionType == "RECEIPT":
                            prior_receipts += mt.Amount
                        else:
                            prior_receipts -= mt.Amount
                for p in c_payments:
                    if p.PaymentID not in seen_payment_ids and p.PaymentDate < from_date:
                        prior_receipts += p.Amount

                # Customer Opening balance = Receipts (Credit) - Sales (Debit)
                # If negative, customer owes money (Baqi)
                opening_balance = prior_receipts - prior_sales

                # Period transactions
                period_sales = sum(s.TotalAmount for s in c_sales if from_date <= s.SaleDate <= to_date)
                period_invoices_count = sum(1 for s in c_sales if from_date <= s.SaleDate <= to_date)

                period_receipts = 0.0
                for mt in c_money:
                    if from_date <= mt.TransactionDate <= to_date:
                        if mt.TransactionType == "RECEIPT":
                            period_receipts += mt.Amount
                        else:
                            period_receipts -= mt.Amount

                for p in c_payments:
                    if p.PaymentID not in seen_payment_ids and from_date <= p.PaymentDate <= to_date:
                        period_receipts += p.Amount

                closing_balance = opening_balance + period_receipts - period_sales

                if closing_balance < 0:
                    status = "RECEIVABLE"
                    baqi_amt = abs(closing_balance)
                    advance_amt = 0.0
                    grand_baqi += baqi_amt
                elif closing_balance > 0:
                    status = "ADVANCE"
                    baqi_amt = 0.0
                    advance_amt = closing_balance
                    grand_advance += advance_amt
                else:
                    status = "BALANCED"
                    baqi_amt = 0.0
                    advance_amt = 0.0

                grand_sales += period_sales
                grand_receipts += period_receipts

                # Only skip if totally zero activity and zero balances
                if opening_balance == 0 and period_sales == 0 and period_receipts == 0 and closing_balance == 0:
                    # Still display if search_text was provided, otherwise skip completely idle
                    if not search_text:
                        continue

                rows.append({
                    "CustomerID": cid,
                    "EnglishName": c.EnglishName,
                    "UrduName": c.UrduName or "",
                    "Mobile": c.Mobile or "",
                    "Address": c.Address or "",
                    "OpeningBalance": opening_balance,
                    "PeriodSales": period_sales,
                    "PeriodReceipts": period_receipts,
                    "InvoicesCount": period_invoices_count,
                    "ClosingBalance": closing_balance,
                    "Status": status,
                    "BaqiAmount": baqi_amt,
                    "AdvanceAmount": advance_amt
                })

            # Sort by highest Baqi receivable first
            rows.sort(key=lambda x: (x["Status"] != "RECEIVABLE", -x["BaqiAmount"], x["EnglishName"]))

            return {
                "rows": rows,
                "kpis": {
                    "total_customers": len(rows),
                    "total_sales": grand_sales,
                    "total_receipts": grand_receipts,
                    "total_baqi": grand_baqi,
                    "total_advance": grand_advance,
                    "net_receivable": grand_baqi - grand_advance
                }
            }

    # =========================================================================
    # 2. LABOUR REGISTER & CATEGORY REPORT (DATE TO DATE)
    # =========================================================================
    @staticmethod
    def get_labour_summary_report(
        from_date: date,
        to_date: date,
        category_name: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate performance for Labourers across all categories or a specific category
        (e.g., Pathera, Bahri Wala, Nakkasi Wala, Jamadar, Jalai Wala).
        Computes:
            - Opening balance
            - Total production count (Bricks / Tiles molded or moved)
            - Total earned wages (Credit)
            - Total payments & advances given (Debit)
            - Net closing balance (Payable or Advance)
        """
        with get_db_session() as session:
            query = session.query(LabourAccount).join(AccountType)
            query = query.filter(LabourAccount.IsOmitted.is_(False))

            if category_name and category_name != "All Labour":
                query = query.filter(AccountType.AccountTypeName == category_name)
            else:
                # Exclude Customer, Owner, and pure Expense categories for labour report
                excluded = ["Customer", "Owner", "Mutfariq Expenses", "Mutfariq Income", "Fixed Assets"]
                query = query.filter(AccountType.AccountTypeName.notin_(excluded))

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        LabourAccount.WorkerID.ilike(s),
                        LabourAccount.EnglishName.ilike(s),
                        LabourAccount.UrduName.ilike(s),
                        LabourAccount.Mobile.ilike(s)
                    )
                )

            workers = query.order_by(AccountType.AccountTypeName.asc(), LabourAccount.EnglishName.asc()).all()
            worker_ids = [w.WorkerID for w in workers]

            if not worker_ids:
                return {
                    "rows": [],
                    "kpis": {
                        "total_workers": 0,
                        "total_production_qty": 0.0,
                        "total_wages_earned": 0.0,
                        "total_advances_paid": 0.0,
                        "total_payable": 0.0,
                        "total_worker_advance": 0.0,
                        "net_payable": 0.0
                    }
                }

            # Pre-fetch labour rates for all these workers
            rates = session.query(LabourRate).filter(LabourRate.WorkerID.in_(worker_ids)).all()
            rates_map: Dict[Tuple[str, int], float] = {(r.WorkerID, r.ProductID): r.RatePer1000 for r in rates}

            # Pre-fetch default product unit rates as fallback
            products = session.query(Product).all()
            prod_rate_map = {p.ProductID: (p.UnitRate or 0.0) for p in products}

            # Pre-fetch all production details for these workers
            prod_details = (
                session.query(ProductionDetail)
                .join(ProductionHeader, ProductionDetail.ProductionID == ProductionHeader.ProductionID)
                .filter(ProductionDetail.WorkerID.in_(worker_ids))
                .options(joinedload(ProductionDetail.header))
                .all()
            )
            prod_map: Dict[str, List[ProductionDetail]] = {wid: [] for wid in worker_ids}
            for pd in prod_details:
                if pd.WorkerID in prod_map:
                    prod_map[pd.WorkerID].append(pd)

            # Pre-fetch money transactions
            money_txns = (
                session.query(MoneyTransaction)
                .filter(
                    MoneyTransaction.AccountID.in_(worker_ids),
                    MoneyTransaction.IsDeleted.is_(False)
                )
                .all()
            )
            money_map: Dict[str, List[MoneyTransaction]] = {wid: [] for wid in worker_ids}
            for mt in money_txns:
                if mt.AccountID in money_map:
                    money_map[mt.AccountID].append(mt)

            # Pre-fetch legacy payments
            legacy_payments = (
                session.query(LabourPayment)
                .filter(LabourPayment.WorkerID.in_(worker_ids))
                .all()
            )
            payment_map: Dict[str, List[LabourPayment]] = {wid: [] for wid in worker_ids}
            for lp in legacy_payments:
                if lp.WorkerID in payment_map:
                    payment_map[lp.WorkerID].append(lp)

            rows = []
            grand_prod_qty = 0.0
            grand_wages = 0.0
            grand_advances = 0.0
            grand_payable = 0.0
            grand_worker_advance = 0.0

            for w in workers:
                wid = w.WorkerID
                w_prod = prod_map.get(wid, [])
                w_money = money_map.get(wid, [])
                w_payments = payment_map.get(wid, [])

                seen_payment_ids = set()
                for mt in w_money:
                    if mt.ReferenceType == "LabourPayment" and mt.ReferenceID and mt.ReferenceID.isdigit():
                        seen_payment_ids.add(int(mt.ReferenceID))

                # Prior Production Earnings (Credit to Worker)
                prior_earnings = 0.0
                for pd in w_prod:
                    if pd.header and pd.header.EntryDate < from_date:
                        rate = rates_map.get((wid, pd.ProductID), prod_rate_map.get(pd.ProductID, 0.0))
                        prior_earnings += (pd.Quantity / 1000.0) * rate

                # Prior Payments (Debit to Worker)
                prior_payments = 0.0
                for mt in w_money:
                    if mt.TransactionDate < from_date:
                        if mt.TransactionType == "PAYMENT":
                            prior_payments += mt.Amount
                        else:
                            prior_payments -= mt.Amount
                for p in w_payments:
                    if p.PaymentID not in seen_payment_ids and p.PaymentDate < from_date:
                        prior_payments += p.Amount

                # Labour Opening Balance = Prior Earnings (Credit) - Prior Payments (Debit)
                # If positive, system owes labour (Payable). If negative, labour has advance taken.
                opening_balance = prior_earnings - prior_payments

                # Period Production & Earnings
                period_qty = 0.0
                period_earnings = 0.0
                for pd in w_prod:
                    if pd.header and from_date <= pd.header.EntryDate <= to_date:
                        period_qty += pd.Quantity
                        rate = rates_map.get((wid, pd.ProductID), prod_rate_map.get(pd.ProductID, 0.0))
                        period_earnings += (pd.Quantity / 1000.0) * rate

                # Period Payments / Advances Paid
                period_payments = 0.0
                for mt in w_money:
                    if from_date <= mt.TransactionDate <= to_date:
                        if mt.TransactionType == "PAYMENT":
                            period_payments += mt.Amount
                        else:
                            period_payments -= mt.Amount

                for p in w_payments:
                    if p.PaymentID not in seen_payment_ids and from_date <= p.PaymentDate <= to_date:
                        period_payments += p.Amount

                closing_balance = opening_balance + period_earnings - period_payments

                if closing_balance > 0:
                    status = "PAYABLE"
                    payable_amt = closing_balance
                    advance_amt = 0.0
                    grand_payable += payable_amt
                elif closing_balance < 0:
                    status = "ADVANCE"
                    payable_amt = 0.0
                    advance_amt = abs(closing_balance)
                    grand_worker_advance += advance_amt
                else:
                    status = "BALANCED"
                    payable_amt = 0.0
                    advance_amt = 0.0

                grand_prod_qty += period_qty
                grand_wages += period_earnings
                grand_advances += period_payments

                if opening_balance == 0 and period_earnings == 0 and period_payments == 0 and closing_balance == 0:
                    if not search_text:
                        continue

                rows.append({
                    "WorkerID": wid,
                    "EnglishName": w.EnglishName,
                    "UrduName": w.UrduName or "",
                    "CategoryName": w.account_type.AccountTypeName if w.account_type else "Labour",
                    "Mobile": w.Mobile or "",
                    "OpeningBalance": opening_balance,
                    "ProductionQty": period_qty,
                    "EarnedWages": period_earnings,
                    "PaymentsPaid": period_payments,
                    "ClosingBalance": closing_balance,
                    "Status": status,
                    "PayableAmount": payable_amt,
                    "AdvanceAmount": advance_amt
                })

            # Sort by Category, then highest Payable
            rows.sort(key=lambda x: (x["CategoryName"], -x["PayableAmount"], x["EnglishName"]))

            return {
                "rows": rows,
                "kpis": {
                    "total_workers": len(rows),
                    "total_production_qty": grand_prod_qty,
                    "total_wages_earned": grand_wages,
                    "total_advances_paid": grand_advances,
                    "total_payable": grand_payable,
                    "total_worker_advance": grand_worker_advance,
                    "net_payable": grand_payable - grand_worker_advance
                }
            }

    # =========================================================================
    # 3. SALES REGISTER & REPORT (DATE TO DATE)
    # =========================================================================
    @staticmethod
    def get_sales_register(
        from_date: date,
        to_date: date,
        customer_id: Optional[str] = None,
        product_id: Optional[int] = None,
        transport_mode: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive Sales Invoicing Register with line items, product breakdown, and totals.
        """
        with get_db_session() as session:
            query = session.query(SalesHeader).join(LabourAccount, SalesHeader.CustomerID == LabourAccount.WorkerID)
            query = query.filter(SalesHeader.SaleDate >= from_date, SalesHeader.SaleDate <= to_date)

            if customer_id and customer_id != "All":
                query = query.filter(SalesHeader.CustomerID == customer_id)

            if transport_mode and transport_mode != "All":
                query = query.filter(SalesHeader.TransportMode == transport_mode)

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        SalesHeader.InvoiceNo.ilike(s),
                        LabourAccount.EnglishName.ilike(s),
                        SalesHeader.VehicleNumber.ilike(s),
                        SalesHeader.DriverName.ilike(s),
                        SalesHeader.Remarks.ilike(s)
                    )
                )

            sales = query.order_by(SalesHeader.SaleDate.desc(), SalesHeader.SaleID.desc()).all()

            rows = []
            total_bricks = 0.0
            total_amount = 0.0

            for sh in sales:
                items_summary = []
                invoice_bricks = 0.0

                for d in sh.details:
                    if product_id and d.ProductID != product_id:
                        continue
                    p_name = d.product.ProductName if d.product else f"Product #{d.ProductID}"
                    items_summary.append(f"{p_name}: {d.Quantity:,.0f} @ Rs.{d.RatePer1000:,.0f}")
                    invoice_bricks += d.Quantity

                # If filtering by specific product and this invoice didn't contain it, skip
                if product_id and not items_summary:
                    continue

                total_bricks += invoice_bricks
                total_amount += sh.TotalAmount

                cust_name = sh.customer.EnglishName if sh.customer else sh.CustomerID
                if sh.customer and sh.customer.UrduName:
                    cust_name += f" ({sh.customer.UrduName})"

                rows.append({
                    "SaleID": sh.SaleID,
                    "InvoiceNo": sh.InvoiceNo,
                    "SaleDate": sh.SaleDate.strftime("%d-%b-%Y"),
                    "RawDate": sh.SaleDate,
                    "CustomerID": sh.CustomerID,
                    "CustomerName": cust_name,
                    "TransportMode": sh.TransportMode or "—",
                    "VehicleNumber": sh.VehicleNumber or "—",
                    "DriverName": sh.DriverName or "—",
                    "ItemsSummary": " | ".join(items_summary) if items_summary else "—",
                    "TotalBricks": invoice_bricks,
                    "TotalAmount": sh.TotalAmount,
                    "Remarks": sh.Remarks or ""
                })

            return {
                "rows": rows,
                "kpis": {
                    "total_invoices": len(rows),
                    "total_bricks_sold": total_bricks,
                    "total_sale_amount": total_amount,
                    "avg_rate_per_k": (total_amount / (total_bricks / 1000.0)) if total_bricks > 0 else 0.0
                }
            }

    # =========================================================================
    # 4. DAILY WORK / PRODUCTION REGISTER (DATE TO DATE)
    # =========================================================================
    @staticmethod
    def get_production_register(
        from_date: date,
        to_date: date,
        category_name: Optional[str] = None,
        worker_id: Optional[str] = None,
        product_id: Optional[int] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detailed Daily Work & Production Register showing worker performance, rates, and wage credits.
        """
        with get_db_session() as session:
            query = (
                session.query(ProductionDetail)
                .join(ProductionHeader, ProductionDetail.ProductionID == ProductionHeader.ProductionID)
                .join(LabourAccount, ProductionDetail.WorkerID == LabourAccount.WorkerID)
                .join(AccountType, LabourAccount.AccountTypeID == AccountType.AccountTypeID)
                .join(Product, ProductionDetail.ProductID == Product.ProductID)
                .filter(ProductionHeader.EntryDate >= from_date, ProductionHeader.EntryDate <= to_date)
            )

            if category_name and category_name != "All Labour":
                query = query.filter(AccountType.AccountTypeName == category_name)

            if worker_id and worker_id != "All":
                query = query.filter(ProductionDetail.WorkerID == worker_id)

            if product_id:
                query = query.filter(ProductionDetail.ProductID == product_id)

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        LabourAccount.EnglishName.ilike(s),
                        LabourAccount.WorkerID.ilike(s),
                        Product.ProductName.ilike(s),
                        ProductionHeader.Remarks.ilike(s)
                    )
                )

            details = query.order_by(ProductionHeader.EntryDate.desc(), ProductionDetail.ProductionDetailID.desc()).all()

            # Pre-fetch labour rates
            worker_ids = list({d.WorkerID for d in details})
            rates = session.query(LabourRate).filter(LabourRate.WorkerID.in_(worker_ids)).all() if worker_ids else []
            rates_map: Dict[Tuple[str, int], float] = {(r.WorkerID, r.ProductID): r.RatePer1000 for r in rates}

            rows = []
            total_qty = 0.0
            total_wages = 0.0

            for d in details:
                wid = d.WorkerID
                pid = d.ProductID
                rate = rates_map.get((wid, pid), d.product.UnitRate or 0.0)
                earned = (d.Quantity / 1000.0) * rate

                total_qty += d.Quantity
                total_wages += earned

                w_name = d.worker.EnglishName if d.worker else wid
                if d.worker and d.worker.UrduName:
                    w_name += f" ({d.worker.UrduName})"

                rows.append({
                    "ProductionID": d.ProductionID,
                    "EntryDate": d.header.EntryDate.strftime("%d-%b-%Y") if d.header else "",
                    "RawDate": d.header.EntryDate if d.header else None,
                    "CategoryName": d.worker.account_type.AccountTypeName if d.worker and d.worker.account_type else "",
                    "WorkerID": wid,
                    "WorkerName": w_name,
                    "ProductID": pid,
                    "ProductName": d.product.ProductName if d.product else f"Product #{pid}",
                    "Quantity": d.Quantity,
                    "RatePer1000": rate,
                    "TotalWage": earned,
                    "Remarks": d.header.Remarks or "" if d.header else ""
                })

            return {
                "rows": rows,
                "kpis": {
                    "total_entries": len(rows),
                    "total_production_qty": total_qty,
                    "total_wages_earned": total_wages,
                    "avg_wage_rate": (total_wages / (total_qty / 1000.0)) if total_qty > 0 else 0.0
                }
            }

    # =========================================================================
    # 5. AMDAN & AKRAJAT (CASHBOOK / FINANCIAL REGISTER)
    # =========================================================================
    @staticmethod
    def get_cashbook_register(
        from_date: date,
        to_date: date,
        txn_type: Optional[str] = None,
        category_name: Optional[str] = None,
        payment_method: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified Cashbook Register with running balance, receipts (Amdan), payments (Akrajat), and methods.
        """
        with get_db_session() as session:
            # First calculate opening balance (prior to from_date)
            prior_txns = (
                session.query(MoneyTransaction)
                .filter(
                    MoneyTransaction.TransactionDate < from_date,
                    MoneyTransaction.IsDeleted.is_(False)
                )
                .all()
            )
            opening_amdan = sum(t.Amount for t in prior_txns if t.TransactionType == "RECEIPT")
            opening_akrajat = sum(t.Amount for t in prior_txns if t.TransactionType == "PAYMENT")
            opening_net_cash = opening_amdan - opening_akrajat

            # Period query
            query = (
                session.query(MoneyTransaction)
                .join(LabourAccount, MoneyTransaction.AccountID == LabourAccount.WorkerID)
                .join(AccountType, LabourAccount.AccountTypeID == AccountType.AccountTypeID)
                .filter(
                    MoneyTransaction.TransactionDate >= from_date,
                    MoneyTransaction.TransactionDate <= to_date,
                    MoneyTransaction.IsDeleted.is_(False)
                )
            )

            if txn_type and txn_type not in ("All", "BOTH"):
                query = query.filter(MoneyTransaction.TransactionType == txn_type)

            if category_name and category_name != "All Categories":
                query = query.filter(AccountType.AccountTypeName == category_name)

            if payment_method and payment_method != "All Methods":
                query = query.filter(MoneyTransaction.PaymentMethod == payment_method)

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        MoneyTransaction.TransactionNo.ilike(s),
                        LabourAccount.EnglishName.ilike(s),
                        MoneyTransaction.Description.ilike(s),
                        MoneyTransaction.BankAccount.ilike(s),
                        MoneyTransaction.ChequeNumber.ilike(s)
                    )
                )

            txns = query.order_by(MoneyTransaction.TransactionDate.asc(), MoneyTransaction.TransactionID.asc()).all()

            rows = []
            period_amdan = 0.0
            period_akrajat = 0.0
            running_cash = opening_net_cash

            for t in txns:
                is_receipt = (t.TransactionType == "RECEIPT")
                credit_amt = t.Amount if is_receipt else 0.0  # Cash in (Amdan)
                debit_amt = 0.0 if is_receipt else t.Amount   # Cash out (Akrajat)

                period_amdan += credit_amt
                period_akrajat += debit_amt
                running_cash += (credit_amt - debit_amt)

                acc_name = t.account.EnglishName if t.account else t.AccountID
                if t.account and t.account.UrduName:
                    acc_name += f" ({t.account.UrduName})"

                rows.append({
                    "TransactionID": t.TransactionID,
                    "TransactionNo": t.TransactionNo,
                    "TransactionDate": t.TransactionDate.strftime("%d-%b-%Y"),
                    "RawDate": t.TransactionDate,
                    "TransactionType": t.TransactionType,
                    "AccountID": t.AccountID,
                    "AccountName": acc_name,
                    "CategoryName": t.account.account_type.AccountTypeName if t.account and t.account.account_type else "General",
                    "PaymentMethod": t.PaymentMethod,
                    "BankAccount": t.BankAccount or "—",
                    "ChequeNumber": t.ChequeNumber or "—",
                    "Description": t.Description,
                    "Amdan": credit_amt,
                    "Akrajat": debit_amt,
                    "RunningCash": running_cash
                })

            # For user presentation, reverse chronological order for table display
            rows_display = list(reversed(rows))

            return {
                "rows": rows_display,
                "kpis": {
                    "opening_cash": opening_net_cash,
                    "total_amdan": period_amdan,
                    "total_akrajat": period_akrajat,
                    "net_period_flow": period_amdan - period_akrajat,
                    "closing_cash": opening_net_cash + period_amdan - period_akrajat,
                    "total_transactions": len(rows)
                }
            }

    # =========================================================================
    # 6. GENERAL ACCOUNT CATEGORIES SUMMARY (OTHER KHATAS)
    # =========================================================================
    @staticmethod
    def get_general_accounts_summary(
        category_name: str,
        from_date: date,
        to_date: date,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summary report for specialized categories like Purchase Party, Transporter, Driver, Owner, etc.
        """
        with get_db_session() as session:
            acc_type = session.query(AccountType).filter_by(AccountTypeName=category_name).first()
            if not acc_type:
                return {"rows": [], "kpis": {}}

            query = session.query(LabourAccount).filter(
                LabourAccount.AccountTypeID == acc_type.AccountTypeID,
                LabourAccount.IsOmitted.is_(False)
            )

            if search_text and search_text.strip():
                s = f"%{search_text.strip()}%"
                query = query.filter(
                    or_(
                        LabourAccount.WorkerID.ilike(s),
                        LabourAccount.EnglishName.ilike(s),
                        LabourAccount.UrduName.ilike(s),
                        LabourAccount.Mobile.ilike(s)
                    )
                )

            accounts = query.order_by(LabourAccount.EnglishName.asc()).all()
            account_ids = [a.WorkerID for a in accounts]

            if not account_ids:
                return {"rows": [], "kpis": {"total_accounts": 0, "total_debit": 0.0, "total_credit": 0.0, "net_balance": 0.0}}

            # Fetch MoneyTransactions
            money_txns = (
                session.query(MoneyTransaction)
                .filter(
                    MoneyTransaction.AccountID.in_(account_ids),
                    MoneyTransaction.IsDeleted.is_(False)
                )
                .all()
            )
            money_map: Dict[str, List[MoneyTransaction]] = {aid: [] for aid in account_ids}
            for mt in money_txns:
                if mt.AccountID in money_map:
                    money_map[mt.AccountID].append(mt)

            rows = []
            grand_debit = 0.0
            grand_credit = 0.0

            for a in accounts:
                aid = a.WorkerID
                a_txns = money_map.get(aid, [])

                prior_credit = sum(t.Amount for t in a_txns if t.TransactionDate < from_date and t.TransactionType == "RECEIPT")
                prior_debit = sum(t.Amount for t in a_txns if t.TransactionDate < from_date and t.TransactionType == "PAYMENT")
                opening_bal = prior_credit - prior_debit

                period_credit = sum(t.Amount for t in a_txns if from_date <= t.TransactionDate <= to_date and t.TransactionType == "RECEIPT")
                period_debit = sum(t.Amount for t in a_txns if from_date <= t.TransactionDate <= to_date and t.TransactionType == "PAYMENT")
                closing_bal = opening_bal + period_credit - period_debit

                grand_credit += period_credit
                grand_debit += period_debit

                if opening_bal == 0 and period_credit == 0 and period_debit == 0 and closing_bal == 0 and not search_text:
                    continue

                status = "CREDIT" if closing_bal > 0 else ("DEBIT" if closing_bal < 0 else "BALANCED")

                rows.append({
                    "AccountID": aid,
                    "EnglishName": a.EnglishName,
                    "UrduName": a.UrduName or "",
                    "CategoryName": category_name,
                    "Mobile": a.Mobile or "",
                    "OpeningBalance": opening_bal,
                    "PeriodCredit": period_credit,
                    "PeriodDebit": period_debit,
                    "ClosingBalance": closing_bal,
                    "Status": status
                })

            return {
                "rows": rows,
                "kpis": {
                    "total_accounts": len(rows),
                    "total_credit": grand_credit,
                    "total_debit": grand_debit,
                    "net_balance": grand_credit - grand_debit
                }
            }
