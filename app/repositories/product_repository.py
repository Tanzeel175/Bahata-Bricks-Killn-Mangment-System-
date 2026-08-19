from datetime import datetime
from typing import Optional, List
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from app.database.schema import Product, ProductCategory, ProductCategoryMapping
from app.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: Session):
        super().__init__(session, Product)

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return (
            self.session.query(Product)
            .options(joinedload(Product.category_mappings).joinedload(ProductCategoryMapping.category))
            .filter(Product.ProductID == product_id)
            .first()
        )

    def get_by_name(self, product_name: str) -> Optional[Product]:
        return (
            self.session.query(Product)
            .filter(func.lower(Product.ProductName) == func.lower(product_name.strip()))
            .first()
        )

    def get_all_categories(self) -> List[ProductCategory]:
        return self.session.query(ProductCategory).order_by(ProductCategory.CategoryID.asc()).all()

    def get_category_by_id(self, category_id: int) -> Optional[ProductCategory]:
        return self.session.query(ProductCategory).filter(ProductCategory.CategoryID == category_id).first()

    def get_category_by_name(self, category_name: str) -> Optional[ProductCategory]:
        return self.session.query(ProductCategory).filter(func.lower(ProductCategory.CategoryName) == func.lower(category_name.strip())).first()

    def search_products(
        self,
        query_str: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> List[Product]:
        q = (
            self.session.query(Product)
            .options(joinedload(Product.category_mappings).joinedload(ProductCategoryMapping.category))
        )

        if category_id and category_id > 0:
            q = q.join(Product.category_mappings).filter(ProductCategoryMapping.CategoryID == category_id)

        if query_str and query_str.strip():
            term = f"%{query_str.strip()}%"
            # Try to match integer product ID or string fields
            try:
                pid = int(query_str.strip())
                q = q.filter(
                    or_(
                        Product.ProductID == pid,
                        Product.ProductName.ilike(term),
                        Product.Description.ilike(term)
                    )
                )
            except ValueError:
                q = q.filter(
                    or_(
                        Product.ProductName.ilike(term),
                        Product.Description.ilike(term)
                    )
                )

        return q.order_by(Product.ProductID.asc()).all()

    def get_products_by_category_name(self, category_name: str) -> List[Product]:
        """
        Dynamic lookup for external modules (Purchase, Sale, Molding).
        Returns all products assigned to the specified category name.
        """
        cat = self.get_category_by_name(category_name)
        if not cat:
            return []

        return (
            self.session.query(Product)
            .join(Product.category_mappings)
            .filter(ProductCategoryMapping.CategoryID == cat.CategoryID)
            .order_by(Product.ProductName.asc())
            .all()
        )

    def save_product(
        self,
        data: dict,
        selected_category_ids: List[int],
        user_name: str = "System"
    ) -> Product:
        product_id = data.get("ProductID")
        product_name = str(data["ProductName"]).strip()
        description = str(data.get("Description", "")).strip() or None
        unit_rate = float(data.get("UnitRate", 0.0) or 0.0)
        stock_quantity = float(data.get("StockQuantity", 0.0) or 0.0)

        if product_id and int(product_id) > 0:
            product = self.get_by_id(int(product_id))
            if product:
                product.ProductName = product_name
                product.Description = description
                product.UnitRate = unit_rate
                product.StockQuantity = stock_quantity
                product.ModifiedBy = user_name
                product.ModifiedDate = datetime.utcnow()

                # Clear old mappings and add updated category mappings
                self.session.query(ProductCategoryMapping).filter(ProductCategoryMapping.ProductID == product.ProductID).delete()
        else:
            product = Product(
                ProductName=product_name,
                Description=description,
                UnitRate=unit_rate,
                StockQuantity=stock_quantity,
                CreatedBy=user_name,
                CreatedDate=datetime.utcnow(),
                ModifiedBy=user_name,
                ModifiedDate=datetime.utcnow()
            )
            self.session.add(product)
            self.session.flush()

        # Add new category mappings
        for cid in selected_category_ids:
            mapping = ProductCategoryMapping(ProductID=product.ProductID, CategoryID=cid)
            self.session.add(mapping)

        self.session.flush()
        return product

    def delete_product(self, product_id: int) -> bool:
        product = self.get_by_id(product_id)
        if product:
            self.session.delete(product)
            self.session.flush()
            return True
        return False
