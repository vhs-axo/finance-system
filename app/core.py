import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Connection Settings
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3322))
DB_USER = os.getenv("DB_USER", "immudb")
DB_PASSWORD = os.getenv("DB_PASSWORD", "immudb")

# Initial Seed Credentials
# These are used ONLY if the database is empty to create the first accounts.
INITIAL_ADMIN_PASS = os.getenv("INITIAL_ADMIN_PASS", "admin123")
INITIAL_STAFF_PASS = os.getenv("INITIAL_STAFF_PASS", "staff123")
INITIAL_AUDITOR_PASS = os.getenv("INITIAL_AUDITOR_PASS", "auditor123")
INITIAL_IT_PASS = os.getenv("INITIAL_IT_PASS", "it123")
INITIAL_PAYABLES_PASS = os.getenv("INITIAL_PAYABLES_PASS", "payables123")
INITIAL_VP_FINANCE_PASS = os.getenv("INITIAL_VP_FINANCE_PASS", "vpfinance123")
INITIAL_PRESIDENT_PASS = os.getenv("INITIAL_PRESIDENT_PASS", "president123")
INITIAL_PROCUREMENT_PASS = os.getenv("INITIAL_PROCUREMENT_PASS", "procurement123")
INITIAL_DEPT_HEAD_PASS = os.getenv("INITIAL_DEPT_HEAD_PASS", "depthead123")
INITIAL_BOOKKEEPER_PASS = os.getenv("INITIAL_BOOKKEEPER_PASS", "bookkeeper123")
INITIAL_STUDENT_PASS = os.getenv("INITIAL_STUDENT_PASS", "student123")