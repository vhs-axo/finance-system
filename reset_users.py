"""
Reset all user accounts. Each role has its own table:
- users: username, hashed_password, role (student | staff | admin | payables | ...), active
- students, staff: one each
- admin, payables, bookkeeper, vp_finance, president, procurement, dept_head, it: each own table
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from immudb import ImmudbClient
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3322))
DB_USER = os.getenv("DB_USER", "immudb")
DB_PASSWORD = os.getenv("DB_PASSWORD", "immudb")

from app.utils import get_password_hash
from app.database import _ensure_new_user_tables, ROLE_TABLES


def esc(s):
    return str(s).replace("'", "''") if s else ""


# (username, password_env_key, default_pass, role, first_name, last_name, contact_info, gender)
ROLE_USERS = [
    ("admin", "INITIAL_ADMIN_PASS", "admin123", "admin", "System", "Administrator", "admin@gmail.com", "Other"),
    ("payables", "INITIAL_PAYABLES_PASS", "payables123", "payables", "Payables", "Associate", "payables@gmail.com", "Other"),
    ("vpfinance", "INITIAL_VP_FINANCE_PASS", "vpfinance123", "vp_finance", "VP", "Finance", "vpfinance@gmail.com", "Other"),
    ("president", "INITIAL_PRESIDENT_PASS", "president123", "president", "President", "Office", "president@gmail.com", "Other"),
    ("procurement", "INITIAL_PROCUREMENT_PASS", "procurement123", "procurement", "Procurement", "Officer", "procurement@gmail.com", "Other"),
    ("depthead", "INITIAL_DEPT_HEAD_PASS", "depthead123", "dept_head", "Department", "Head", "depthead@gmail.com", "Other"),
    ("bookkeeper", "INITIAL_BOOKKEEPER_PASS", "bookkeeper123", "bookkeeper", "Bookkeeper", "Account", "bookkeeper@gmail.com", "Other"),
]

STAFF_USER = (
    "staff",
    "INITIAL_STAFF_PASS",
    "staff123",
    "Finance", "", "Staff",
    "Other", "Finance Officer", "Finance", "2024-01-15", "Active", 45000,
)

STUDENT_USER = ("student", "123", "Student", "", "Account", "Other", "Other", "", "plan_a")


def reset_users():
    try:
        print(f"Connecting to Immudb at {DB_HOST}:{DB_PORT}...")
        client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
        client.login(DB_USER, DB_PASSWORD)
        print("✅ Connected to database")

        print("\n🔧 Ensuring user tables exist...")
        _ensure_new_user_tables(client)

        print("\n🗑️  Deleting existing users and role data...")
        for table in ["students", "staff"] + ROLE_TABLES:
            try:
                client.sqlExec(f"DELETE FROM {table}")
                print(f"  Cleared {table}")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")
        try:
            client.sqlExec("DELETE FROM users")
            print("  Cleared users")
        except Exception as e:
            print(f"  ⚠️  users: {e}")

        print("\n👥 Creating role users (admin, payables, ...)...")
        for username, env_key, default_pass, role, first_name, last_name, contact, gender in ROLE_USERS:
            password = os.getenv(env_key, default_pass)
            hashed = get_password_hash(password)
            client.sqlExec(
                f"INSERT INTO users (username, hashed_password, role, active) "
                f"VALUES ('{esc(username)}', '{esc(hashed)}', '{esc(role)}', true)"
            )
            client.sqlExec(
                f"INSERT INTO {role} (username, first_name, middle_name, last_name, gender, contact_information) "
                f"VALUES ('{esc(username)}', '{esc(first_name)}', '', '{esc(last_name)}', '{esc(gender)}', '{esc(contact)}')"
            )
            print(f"  ✅ {username} ({role})")

        print("\n👤 Creating staff user...")
        (username, env_key, default_pass, fn, mn, ln, gender, position, department, date_hired, status, monthly_salary) = STAFF_USER
        password = os.getenv(env_key, default_pass)
        hashed = get_password_hash(password)
        client.sqlExec(
            f"INSERT INTO users (username, hashed_password, role, active) "
            f"VALUES ('{esc(username)}', '{esc(hashed)}', 'staff', true)"
        )
        client.sqlExec(
            f"INSERT INTO staff (username, first_name, middle_name, last_name, gender, position, department, date_hired, status, monthly_salary) "
            f"VALUES ('{esc(username)}', '{esc(fn)}', '{esc(mn)}', '{esc(ln)}', '{esc(gender)}', "
            f"'{esc(position)}', '{esc(department)}', '{esc(date_hired)}', '{esc(status)}', {int(monthly_salary)})"
        )
        print(f"  ✅ {username} (staff)")

        print("\n👤 Creating student user...")
        username, password, first_name, middle_name, last_name, gender, strand, section, payment_plan = STUDENT_USER
        hashed = get_password_hash(password)
        client.sqlExec(
            f"INSERT INTO users (username, hashed_password, role, active) "
            f"VALUES ('{esc(username)}', '{esc(hashed)}', 'student', true)"
        )
        client.sqlExec(
            f"INSERT INTO students (username, first_name, middle_name, last_name, gender, strand, section, payment_plan) "
            f"VALUES ('{esc(username)}', '{esc(first_name)}', '{esc(middle_name)}', '{esc(last_name)}', '{esc(gender)}', '{esc(strand)}', '{esc(section)}', '{esc(payment_plan)}')"
        )
        print(f"  ✅ {username} (student)")

        print("\n✅ User reset completed successfully!")
        print("\n📋 Accounts (login with these usernames):")
        print("-" * 50)
        for username, env_key, default_pass, role, *_ in ROLE_USERS:
            p = os.getenv(env_key, default_pass)
            print(f"  {username} ({role}) / {p}")
        print(f"  {STAFF_USER[0]} (staff) / {os.getenv(STAFF_USER[1], STAFF_USER[2])}")
        print(f"  {STUDENT_USER[0]} (student) / {STUDENT_USER[1]}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("  USER ACCOUNT RESET (users + role tables: admin, payables, staff, students)")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete ALL existing users and role data!")
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() in ["yes", "y"]:
        reset_users()
    else:
        print("❌ Operation cancelled.")
