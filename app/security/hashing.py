import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt."""
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hashed password string."""
    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False
