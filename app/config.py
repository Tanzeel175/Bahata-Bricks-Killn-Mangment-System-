import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
# Default fallback to SQLite database file in BASE_DIR if MSSQL is not configured
DB_TYPE = os.getenv("BAHTA_DB_TYPE", "sqlite")  # 'sqlite' or 'mssql'
SQLITE_PATH = os.getenv("BAHTA_SQLITE_PATH", str(BASE_DIR / "bahta_system.db"))

# MSSQL parameters (used if DB_TYPE == 'mssql')
MSSQL_SERVER = os.getenv("BAHTA_MSSQL_SERVER", "localhost")
MSSQL_DATABASE = os.getenv("BAHTA_MSSQL_DB", "BahtaDB")
MSSQL_DRIVER = os.getenv("BAHTA_MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
MSSQL_USER = os.getenv("BAHTA_MSSQL_USER", "sa")
MSSQL_PASSWORD = os.getenv("BAHTA_MSSQL_PASS", "YourPassword123")

def get_database_url() -> str:
    if DB_TYPE == "mssql":
        return f"mssql+pyodbc://{MSSQL_USER}:{MSSQL_PASSWORD}@{MSSQL_SERVER}/{MSSQL_DATABASE}?driver={MSSQL_DRIVER.replace(' ', '+')}"
    return f"sqlite:///{SQLITE_PATH}"

# Security settings
MAX_FAILED_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT_MINUTES = 15

# App Branding
APP_NAME = "BAHTA MANAGEMENT SYSTEM"
APP_SUBTITLE = "Brick Kiln Enterprise ERP"
COMPANY_NAME = "Bahta Kiln Operations Ltd."
APP_VERSION = "1.0.0"

# User Credentials File for "Remember Username"
USER_PREFS_FILE = BASE_DIR / ".user_prefs.json"
