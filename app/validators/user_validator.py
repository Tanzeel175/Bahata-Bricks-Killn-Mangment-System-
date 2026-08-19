import re
from typing import List, Tuple


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validates password against complexity requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain at least one number (0-9).")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("Password must contain at least one special character (!@#$%^&* etc.).")

    return len(errors) == 0, errors


def validate_username(username: str) -> Tuple[bool, str]:
    if not username or not username.strip():
        return False, "Username cannot be empty."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not re.match(r"^[a-zA-Z0-9_.]+$", username):
        return False, "Username can only contain letters, numbers, dots, and underscores."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    if not email or not email.strip():
        return True, ""  # Email is optional
    email = email.strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False, "Invalid email address format."
    return True, ""
