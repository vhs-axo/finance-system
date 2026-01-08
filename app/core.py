import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Connection Settings
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3322))
DB_USER = os.getenv("DB_USER", "immudb")
DB_PASSWORD = os.getenv("DB_PASSWORD", "immudb")

# Default admin credentials for the initial seed
INITIAL_ADMIN_PASS = os.getenv("INITIAL_ADMIN_PASS", "admin123")
INITIAL_STAFF_PASS = os.getenv("INITIAL_STAFF_PASS", "staff123")
INITIAL_AUDITOR_PASS = os.getenv("INITIAL_AUDITOR_PASS", "auditor123")
