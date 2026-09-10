from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from app.database.connection import get_db_session
from app.repositories.product_repository import ProductRepository
from app.repositories.audit_repository import AuditRepository
from app.security.rbac import can_delete_records, require_authenticated
from app.security.session import current_session
from app.validators.product_validator import validate_product_data


class ProductService:
    """Service layer for Dynamic Product Master management."""

    @staticmethod
    def generate_product_id() -> str:
        with get_db_session() as session:
            repo = ProductRepository(session)
            all_prods = repo.get_all()
            if not all_prods:
                next_num = 1
            else:
                max_id = max(p.ProductID for p in all_prods)
                next_num = max_id + 1
            return f"PRD-{next_num:04d}"

    @staticmethod
    def get_all_categories() -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductRepository(session)
            categories = repo.get_all_categories()
            return [
                {
                    "CategoryID": cat.CategoryID,
                    "CategoryName": cat.CategoryName
                }
                for cat in categories
            ]

    @staticmethod
    def search_products(
        query_str: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductRepository(session)
            products = repo.search_products(query_str, category_id)

            results = []
            for p in products:
                cat_names = [m.category.CategoryName for m in p.category_mappings if m.category]
                cat_ids = [m.CategoryID for m in p.category_mappings]
                live_stock = getattr(p, "StockQuantity", 0.0) or 0.0
                is_system = getattr(p, "IsSystemProduct", False) or (p.ProductName in ["Kacchi Brick", "Kacchi Tile", "Awal", "Doam", "Khinger", "Tile"])

                results.append({
                    "ProductID": p.ProductID,
                    "ProductName": p.ProductName,
                    "Description": p.Description or "",
                    "UnitRate": p.UnitRate or 0.0,
                    "StockQuantity": live_stock,
                    "TotalStockValue": (p.UnitRate or 0.0) * live_stock,
                    "IsSystemProduct": is_system,
                    "CategoryNames": ", ".join(cat_names),
                    "CategoryIDs": cat_ids,
                    "CreatedBy": p.CreatedBy or "",
                    "CreatedDate": p.CreatedDate.strftime("%Y-%m-%d") if p.CreatedDate else ""
                })
            return results

    @staticmethod
    def get_products_by_category(category_name: str) -> List[Dict[str, Any]]:
        """
        Dynamic helper for external modules.
        Returns all products assigned to the specified category name.
        """
        with get_db_session() as session:
            repo = ProductRepository(session)
            products = repo.get_products_by_category_name(category_name)
            return [
                {
                    "ProductID": p.ProductID,
                    "ProductName": p.ProductName,
                    "Description": p.Description or "",
                    "UnitRate": p.UnitRate or 0.0,
                    "StockQuantity": getattr(p, "StockQuantity", 0.0) or 0.0,
                    "TotalStockValue": (p.UnitRate or 0.0) * (getattr(p, "StockQuantity", 0.0) or 0.0)
                }
                for p in products
            ]

    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
        with get_db_session() as session:
            repo = ProductRepository(session)
            p = repo.get_by_id(product_id)
            if not p:
                return None

            cat_names = [m.category.CategoryName for m in p.category_mappings if m.category]
            cat_ids = [m.CategoryID for m in p.category_mappings]
            live_stock = getattr(p, "StockQuantity", 0.0) or 0.0
            is_system = getattr(p, "IsSystemProduct", False) or (p.ProductName in ["Kacchi Brick", "Kacchi Tile", "Awal", "Doam", "Khinger", "Tile"])

            return {
                "ProductID": p.ProductID,
                "ProductName": p.ProductName,
                "Description": p.Description or "",
                "UnitRate": p.UnitRate or 0.0,
                "StockQuantity": live_stock,
                "TotalStockValue": (p.UnitRate or 0.0) * live_stock,
                "IsSystemProduct": is_system,
                "CategoryNames": ", ".join(cat_names),
                "CategoryIDs": cat_ids
            }

    @staticmethod
    @require_authenticated
    def save_product(
        data: Dict[str, Any],
        selected_category_ids: List[int],
        is_edit_mode: bool = False
    ) -> Tuple[bool, str]:
        # Validate data
        val_success, val_msg = validate_product_data(data, selected_category_ids)
        if not val_success:
            return False, val_msg

        product_name = str(data["ProductName"]).strip()
        product_id = data.get("ProductID")

        user_name = current_session.username or "System"

        with get_db_session() as session:
            repo = ProductRepository(session)
            audit_repo = AuditRepository(session)

            # Check uniqueness
            existing = repo.get_by_name(product_name)
            if existing:
                if not is_edit_mode or (product_id and existing.ProductID != int(product_id)):
                    return False, f"Product Name '{product_name}' already exists. Product names must be unique."

            product = repo.save_product(data, selected_category_ids, user_name=user_name)

            action = "PRODUCT_UPDATE" if is_edit_mode else "PRODUCT_CREATE"
            audit_repo.log_event(
                action=action,
                username=user_name,
                user_id=current_session.user_id,
                details=f"{action}: ProductID={product.ProductID}, Name='{product.ProductName}'"
            )
            session.commit()

            msg = f"Product '{product.ProductName}' updated successfully." if is_edit_mode else f"Product '{product.ProductName}' created successfully with ID {product.ProductID}."
            return True, msg

    @staticmethod
    @require_authenticated
    def delete_product(product_id: int) -> Tuple[bool, str]:
        if not can_delete_records():
            return False, "Access Denied: Only Administrator role is permitted to delete products."

        user_name = current_session.username or "System"

        with get_db_session() as session:
            repo = ProductRepository(session)
            audit_repo = AuditRepository(session)

            product = repo.get_by_id(product_id)
            if not product:
                return False, f"Product ID {product_id} not found."

            p_name = product.ProductName

            core_system_prods = [
                "Kacchi Brick (Pathera)", "Kacchi Brick (Bahari)",
                "Kacchi Tile (Pathera)", "Kacchi Tile (Bahari)",
                "Awal", "Doam", "Khinger", "Tile"
            ]
            is_system = getattr(product, "IsSystemProduct", False) or (p_name in core_system_prods)
            if is_system:
                return False, f"Protected System Product: '{p_name}' is a precreated core product linked to Production & Sales forms and cannot be deleted."

            deleted = repo.delete_product(product_id)
            if deleted:
                audit_repo.log_event(
                    action="PRODUCT_DELETE",
                    username=user_name,
                    user_id=current_session.user_id,
                    details=f"PRODUCT_DELETE: ProductID={product_id}, Name='{p_name}'"
                )
                session.commit()
                return True, f"Product '{p_name}' deleted successfully."
            else:
                return False, f"Failed to delete Product ID {product_id}."
