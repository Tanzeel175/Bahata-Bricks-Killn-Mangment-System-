from typing import Tuple, List, Dict, Any


def validate_product_data(data: Dict[str, Any], selected_category_ids: List[int]) -> Tuple[bool, List[str]]:
    """
    Validate product creation and update rules:
    - Product Name is mandatory and max length 100.
    - At least one Product Category must be selected.
    - Description is optional, max length 500.
    """
    errors = []

    product_name = str(data.get("ProductName", "")).strip()
    if not product_name:
        errors.append("Product Name is mandatory.")
    elif len(product_name) > 100:
        errors.append("Product Name cannot exceed 100 characters.")

    if not selected_category_ids or len(selected_category_ids) == 0:
        errors.append("At least one Product Category must be selected.")

    description = str(data.get("Description", "")).strip()
    if description and len(description) > 500:
        errors.append("Description cannot exceed 500 characters.")

    try:
        rate = float(data.get("UnitRate", 0.0) or 0.0)
        if rate < 0:
            errors.append("Product Rate cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Product Rate must be a valid number.")

    try:
        stock = float(data.get("StockQuantity", 0.0) or 0.0)
        if stock < 0:
            errors.append("In Stock Quantity cannot be negative.")
    except (ValueError, TypeError):
        errors.append("In Stock Quantity must be a valid number.")

    return len(errors) == 0, errors
