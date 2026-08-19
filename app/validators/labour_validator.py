import re
from typing import List, Tuple, Dict, Any


def format_cnic(cnic_raw: str) -> str:
    """Format raw 13-digit CNIC into XXXXX-XXXXXXX-X format."""
    digits = re.sub(r"\D", "", cnic_raw or "")
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return cnic_raw.strip()


def validate_cnic(cnic: str) -> Tuple[bool, str]:
    """Validate CNIC against 35202-1234567-1 format if provided."""
    if not cnic or not cnic.strip():
        return True, ""
    cnic = cnic.strip()

    # Check formatted regex
    pattern = r"^\d{5}-\d{7}-\d{1}$"
    if re.match(pattern, cnic):
        return True, ""

    # Check raw 13 digits
    digits = re.sub(r"\D", "", cnic)
    if len(digits) == 13:
        return True, ""

    return False, "Invalid CNIC format. Expected 13 digits (e.g. 35202-1234567-1)."


def format_mobile(mobile_raw: str) -> str:
    """Format Pakistan mobile number."""
    if not mobile_raw:
        return ""
    digits = re.sub(r"\D", "", mobile_raw)
    if digits.startswith("92") and len(digits) == 12:
        return f"+92{digits[2:]}"
    elif digits.startswith("0") and len(digits) == 11:
        return digits
    elif len(digits) == 10 and digits.startswith("3"):
        return f"0{digits}"
    return mobile_raw.strip()


def validate_mobile(mobile: str, field_name: str = "Mobile number") -> Tuple[bool, str]:
    """Validate Pakistan mobile number if provided."""
    if not mobile or not mobile.strip():
        return True, ""
    mobile = mobile.strip()

    pattern = r"^(\+92|0)3\d{9}$"
    digits_only = re.sub(r"[\s\-]", "", mobile)

    if re.match(pattern, digits_only) or len(digits_only) >= 10:
        return True, ""

    return False, f"Invalid {field_name}. Expected format: 03001234567 or +923001234567."


def validate_labour_account(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Comprehensive validation of LabourAccount creation/edit fields."""
    errors = []

    # Worker ID
    worker_id = data.get("WorkerID")
    if not worker_id or not str(worker_id).strip():
        errors.append("Worker ID is required.")

    # Account Type
    account_type_id = data.get("AccountTypeID")
    if not account_type_id:
        errors.append("Account Type is required.")

    # English Name
    english_name = data.get("EnglishName")
    if not english_name or not str(english_name).strip():
        errors.append("English Name is required.")
    elif len(str(english_name).strip()) > 100:
        errors.append("English Name cannot exceed 100 characters.")

    # CNIC (Optional)
    if data.get("CNIC", "") and str(data.get("CNIC", "")).strip():
        valid_cnic, cnic_err = validate_cnic(data.get("CNIC", ""))
        if not valid_cnic:
            errors.append(cnic_err)

    # Mobile (Optional)
    if data.get("Mobile", "") and str(data.get("Mobile", "")).strip():
        valid_mob, mob_err = validate_mobile(data.get("Mobile", ""), "Mobile Number")
        if not valid_mob:
            errors.append(mob_err)

    # Reference Mobile (Optional)
    if data.get("ReferenceMobile", "") and str(data.get("ReferenceMobile", "")).strip():
        valid_ref_mob, ref_mob_err = validate_mobile(data.get("ReferenceMobile", ""), "Reference Mobile")
        if not valid_ref_mob:
            errors.append(ref_mob_err)

    # Targets
    modular_target = data.get("DailyModularTarget", 0)
    try:
        modular_val = float(modular_target)
        if modular_val < 0:
            errors.append("Daily Modular Target cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Daily Modular Target must be a valid number.")

    filler_target = data.get("DailyFillerTarget", 0)
    try:
        filler_val = float(filler_target)
        if filler_val < 0:
            errors.append("Daily Filler Target cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Daily Filler Target must be a valid number.")

    # Email
    email = data.get("Email")
    if email and str(email).strip():
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", str(email).strip()):
            errors.append("Invalid email address format.")

    return len(errors) == 0, errors
