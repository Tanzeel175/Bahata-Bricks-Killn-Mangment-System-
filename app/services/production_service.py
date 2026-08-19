from datetime import datetime, date
from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.database.schema import AccountType
from app.repositories.production_repository import ProductionRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.labour_repository import LabourRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.audit_repository import AuditRepository
from app.security.rbac import can_delete_records
from app.security.session import current_session


class ProductionService:
    """Service facade for Production Entry, Rate Management & Automatic Labour Ledger (Khata)."""

    # --- PRODUCTION ENTRIES ---
    @staticmethod
    def save_production_entry(
        entry_date: date,
        account_type_id: int,
        remarks: Optional[str],
        details_list: List[Dict[str, Any]],
        production_id: Optional[int] = None,
        is_edit_mode: bool = False
    ) -> Tuple[bool, str]:
        if not details_list or len(details_list) == 0:
            return False, "No production details entered. Please enter production quantities."

        # Validate non-negative quantities
        for d in details_list:
            qty = float(d.get("Quantity", 0.0) or 0.0)
            if qty < 0:
                return False, f"Negative quantity '{qty}' is not allowed."

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                rate_repo = RateRepository(session)
                labour_repo = LabourRepository(session)
                product_repo = ProductRepository(session)

                # STRICT VALIDATION: Check category-product compatibility and labour rates
                acc_type = session.query(AccountType).filter_by(AccountTypeID=account_type_id).first()
                cat_name_lower = acc_type.AccountTypeName.strip().lower() if acc_type else ""

                for d in details_list:
                    qty = float(d.get("Quantity", 0.0) or 0.0)
                    if qty > 0.0:
                        wid = str(d["WorkerID"]).strip()
                        pid = int(d["ProductID"])
                        prod = product_repo.get_by_id(pid)
                        p_name = prod.ProductName if prod else f"Product ID {pid}"
                        p_name_lower = p_name.lower()

                        if "pathera" in cat_name_lower:
                            if "kacchi" not in p_name_lower and "pathera" not in p_name_lower:
                                return False, f"Category Restriction: Pathera can ONLY mold raw unbaked bricks/tiles (Kacchi Bricks / Kacchi Tiles). Product '{p_name}' is not allowed for Pathera."
                        elif "bahari" in cat_name_lower or "bahri" in cat_name_lower or "bharai" in cat_name_lower:
                            if "bahari" not in p_name_lower and "bahri" not in p_name_lower and "kacchi" not in p_name_lower:
                                return False, f"Category Restriction: Bahari Wala can ONLY record loading of green bricks/tiles (Kacchi Bricks / Kacchi Tiles). Product '{p_name}' is not allowed for Bahari."
                        elif "nakkasi" in cat_name_lower:
                            if "kacchi" in p_name_lower:
                                return False, f"Category Restriction: Nakkasi Wala can ONLY record finished baked bricks (Awal, Doam, Khinger, Tile). Product '{p_name}' is not allowed for Nakkasi."

                        rate = rate_repo.get_rate(wid, pid)
                        if rate <= 0.0:
                            acc = labour_repo.get_by_worker_id(wid)
                            w_name = acc.EnglishName if acc else wid
                            return False, f"Labour rate is not set for Worker '{wid} - {w_name}' on Product '{p_name}'. Please set the rate in Labour Rates module first."

                repo = ProductionRepository(session)
                audit_repo = AuditRepository(session)

                header = repo.save_production_entry(
                    entry_date=entry_date,
                    account_type_id=account_type_id,
                    remarks=remarks,
                    details_list=details_list,
                    production_id=production_id,
                    user_name=user_name
                )

                action = "PRODUCTION_UPDATE" if is_edit_mode else "PRODUCTION_CREATE"
                audit_repo.log_event(
                    action=action,
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"{action}: ProductionID={header.ProductionID}, Date={header.EntryDate}, Rows={len(details_list)}"
                )
                session.commit()

                msg = f"Production Entry PRD-{header.ProductionID:04d} updated and posted to Labour Khata." if is_edit_mode else f"Production Entry PRD-{header.ProductionID:04d} created and posted to Labour Khata."
                return True, msg
        except Exception as e:
            return False, f"Failed to save production entry: {e}"

    @staticmethod
    def delete_production_entry(production_id: int) -> Tuple[bool, str]:
        if not can_delete_records():
            return False, "Access Denied: Only Administrator role is permitted to delete production entries."

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                repo = ProductionRepository(session)
                audit_repo = AuditRepository(session)

                entry = repo.get_by_id(production_id)
                if not entry:
                    return False, f"Production Entry PRD-{production_id:04d} not found."

                deleted = repo.delete_production_entry(production_id)
                if deleted:
                    audit_repo.log_event(
                        action="PRODUCTION_DELETE",
                        username=user_name,
                        user_id=current_session.user_id,
                        details=f"PRODUCTION_DELETE: ProductionID={production_id} and related ledger entries reversed."
                    )
                    session.commit()
                    return True, f"Production Entry PRD-{production_id:04d} deleted and Khata entries reversed successfully."
                else:
                    return False, f"Production Entry PRD-{production_id:04d} not found."
        except Exception as e:
            return False, f"Failed to delete production entry: {e}"

    @staticmethod
    def search_production_entries(
        account_type_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductionRepository(session)
            entries = repo.search_production_entries(account_type_id, start_date, end_date)
            return [
                {
                    "ProductionID": e.ProductionID,
                    "EntryDate": e.EntryDate.strftime("%Y-%m-%d") if e.EntryDate else "",
                    "AccountTypeID": e.AccountTypeID,
                    "AccountTypeName": e.account_type.AccountTypeName if e.account_type else "",
                    "Remarks": e.Remarks or "",
                    "CreatedBy": e.CreatedBy or "",
                    "CreatedDate": e.CreatedDate.strftime("%Y-%m-%d") if e.CreatedDate else ""
                }
                for e in entries
            ]

    @staticmethod
    def search_production_entries(
        account_type_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductionRepository(session)
            entries = repo.search_production_entries(account_type_id, start_date, end_date)
            return [
                {
                    "ProductionID": e.ProductionID,
                    "EntryDate": e.EntryDate.strftime("%Y-%m-%d") if e.EntryDate else "",
                    "AccountTypeID": e.AccountTypeID,
                    "AccountTypeName": e.account_type.AccountTypeName if e.account_type else "",
                    "CategoryName": e.account_type.AccountTypeName if e.account_type else "",
                    "Remarks": e.Remarks or "",
                    "CreatedBy": e.CreatedBy or ""
                }
                for e in entries
            ]

    @staticmethod
    def get_production_entry_by_id(production_id: int) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductionRepository(session)
            e = repo.get_by_id(production_id)
            if not e:
                return None

            details = []
            for d in e.details:
                details.append({
                    "ProductionDetailID": d.ProductionDetailID,
                    "WorkerID": d.WorkerID,
                    "WorkerName": d.worker.EnglishName if d.worker else "",
                    "ProductID": d.ProductID,
                    "ProductName": d.product.ProductName if d.product else "",
                    "Quantity": d.Quantity
                })

            return {
                "ProductionID": e.ProductionID,
                "EntryDate": e.EntryDate.strftime("%Y-%m-%d") if e.EntryDate else "",
                "AccountTypeID": e.AccountTypeID,
                "AccountTypeName": e.account_type.AccountTypeName if e.account_type else "",
                "Remarks": e.Remarks or "",
                "CreatedBy": e.CreatedBy or "",
                "CreatedDate": e.CreatedDate.strftime("%Y-%m-%d %H:%M") if e.CreatedDate else "",
                "Details": details
            }

    @staticmethod
    def get_production_entry_by_date_and_category(entry_date: date, account_type_id: int) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductionRepository(session)
            e = repo.get_by_date_and_category(entry_date, account_type_id)
            if not e:
                return None

            details = []
            for d in e.details:
                details.append({
                    "ProductionDetailID": d.ProductionDetailID,
                    "WorkerID": d.WorkerID,
                    "WorkerName": d.worker.EnglishName if d.worker else "",
                    "ProductID": d.ProductID,
                    "ProductName": d.product.ProductName if d.product else "",
                    "Quantity": d.Quantity
                })

            return {
                "ProductionID": e.ProductionID,
                "EntryDate": e.EntryDate.strftime("%Y-%m-%d") if e.EntryDate else "",
                "AccountTypeID": e.AccountTypeID,
                "AccountTypeName": e.account_type.AccountTypeName if e.account_type else "",
                "Remarks": e.Remarks or "",
                "CreatedBy": e.CreatedBy or "",
                "CreatedDate": e.CreatedDate.strftime("%Y-%m-%d %H:%M") if e.CreatedDate else "",
                "Details": details
            }

    # --- LABOUR RATE MANAGEMENT ---
    @staticmethod
    def save_worker_rates(worker_id: str, rate_dict: Dict[int, float]) -> Tuple[bool, str]:
        # Validate rates non-negative
        for pid, r in rate_dict.items():
            if r < 0:
                return False, f"Negative rate '{r}' is not allowed."

        user_name = current_session.username or "System"

        try:
            with get_db_session() as session:
                repo = RateRepository(session)
                audit_repo = AuditRepository(session)

                repo.save_worker_rates(worker_id, rate_dict, user_name)

                audit_repo.log_event(
                    action="RATE_UPDATE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"RATE_UPDATE: WorkerID={worker_id}, RatesUpdated={len(rate_dict)}"
                )
                session.commit()
                return True, f"Labour payment rates for Worker '{worker_id}' saved successfully."
        except Exception as e:
            return False, f"Failed to save labour rates: {e}"

    @staticmethod
    def get_worker_rates(worker_id: str) -> Dict[int, float]:
        with get_db_session() as session:
            repo = RateRepository(session)
            return repo.get_worker_rates(worker_id)

    @staticmethod
    def get_transportation_reconciliation_summary() -> Dict[str, Any]:
        """
        Compares Pathera molded green bricks vs Bahari loaded green bricks and Pathera damage
        to verify transport security and detect discrepancies/missing bricks.
        """
        from app.database.schema import ProductionDetail, ProductionHeader, AccountType, DamageDetail, DamageHeader, DamageStage
        from sqlalchemy import func

        with get_db_session() as session:
            # 1. Total Pathera Molded Bricks
            pathera_cat = session.query(AccountType).filter(AccountType.AccountTypeName.ilike("%pathera%")).first()
            pathera_cat_id = pathera_cat.AccountTypeID if pathera_cat else None

            pathera_qty = (
                session.query(func.coalesce(func.sum(ProductionDetail.Quantity), 0.0))
                .join(ProductionHeader, ProductionHeader.ProductionID == ProductionDetail.ProductionID)
                .filter(ProductionHeader.AccountTypeID == pathera_cat_id)
                .scalar() if pathera_cat_id else 0.0
            )

            # 2. Total Bahari Loaded Bricks
            bahari_cat = session.query(AccountType).filter(
                (AccountType.AccountTypeName.ilike("%bahari%")) | (AccountType.AccountTypeName.ilike("%bahri%"))
            ).first()
            bahari_cat_id = bahari_cat.AccountTypeID if bahari_cat else None

            bahari_qty = (
                session.query(func.coalesce(func.sum(ProductionDetail.Quantity), 0.0))
                .join(ProductionHeader, ProductionHeader.ProductionID == ProductionDetail.ProductionID)
                .filter(ProductionHeader.AccountTypeID == bahari_cat_id)
                .scalar() if bahari_cat_id else 0.0
            )

            # 3. Total Pathera Stage Damage
            pathera_stage = session.query(DamageStage).filter(DamageStage.StageName.ilike("%pathera%")).first()
            pathera_stage_id = pathera_stage.StageID if pathera_stage else None

            pathera_damage = (
                session.query(func.coalesce(func.sum(DamageDetail.Quantity), 0.0))
                .join(DamageHeader, DamageHeader.DamageID == DamageDetail.DamageID)
                .filter(DamageHeader.StageID == pathera_stage_id)
                .scalar() if pathera_stage_id else 0.0
            )

            total_pathera = float(pathera_qty or 0.0)
            total_bahari = float(bahari_qty or 0.0)
            total_pathera_dmg = float(pathera_damage or 0.0)

            expected_transport = max(0.0, total_pathera - total_pathera_dmg)
            variance = total_bahari - expected_transport

            if variance == 0.0:
                status_text = "MATCH: Equal Transport Quantities"
                status_color = "#059669"
            elif variance < 0:
                status_text = f"DISCREPANCY: Missing {abs(variance):,.0f} Bricks in Transport"
                status_color = "#E11D48"
            else:
                status_text = f"SURPLUS: +{variance:,.0f} Bricks Loaded"
                status_color = "#0284C7"

            return {
                "PatheraMolded": total_pathera,
                "BahariLoaded": total_bahari,
                "PatheraDamage": total_pathera_dmg,
                "ExpectedTransport": expected_transport,
                "Variance": variance,
                "StatusText": status_text,
                "StatusColor": status_color
            }
