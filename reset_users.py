"""
Script to reset all user accounts in the database.
This script deletes all existing users and creates new ones with:
- Simple usernames (e.g., admin, bookkeeper)
- Email format contact info (e.g., admin@gmail.com)
- Default passwords from .env file
- Proper roles and profile information
"""

import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from immudb import ImmudbClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection settings
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3322))
DB_USER = os.getenv("DB_USER", "immudb")
DB_PASSWORD = os.getenv("DB_PASSWORD", "immudb")

# Password imports
from app.utils import get_password_hash

# User definitions with simple usernames and email format contact info
# strand and payment_plan: used for students; others get strand "Other", payment_plan ""
USERS = [
    {
        "username": "admin",
        "password": os.getenv("INITIAL_ADMIN_PASS", "admin123"),
        "role": "admin",
        "first_name": "System",
        "last_name": "Administrator",
        "contact_info": "admin@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "payables",
        "password": os.getenv("INITIAL_PAYABLES_PASS", "payables123"),
        "role": "payables",
        "first_name": "Payables",
        "last_name": "Associate",
        "contact_info": "payables@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "vpfinance",
        "password": os.getenv("INITIAL_VP_FINANCE_PASS", "vpfinance123"),
        "role": "vp_finance",
        "first_name": "VP",
        "last_name": "Finance",
        "contact_info": "vpfinance@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "president",
        "password": os.getenv("INITIAL_PRESIDENT_PASS", "president123"),
        "role": "president",
        "first_name": "President",
        "last_name": "Office",
        "contact_info": "president@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "procurement",
        "password": os.getenv("INITIAL_PROCUREMENT_PASS", "procurement123"),
        "role": "procurement",
        "first_name": "Procurement",
        "last_name": "Officer",
        "contact_info": "procurement@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "depthead",
        "password": os.getenv("INITIAL_DEPT_HEAD_PASS", "depthead123"),
        "role": "dept_head",
        "first_name": "Department",
        "last_name": "Head",
        "contact_info": "depthead@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "bookkeeper",
        "password": os.getenv("INITIAL_BOOKKEEPER_PASS", "bookkeeper123"),
        "role": "bookkeeper",
        "first_name": "Bookkeeper",
        "last_name": "Account",
        "contact_info": "bookkeeper@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "",
    },
    {
        "username": "student",
        "password": "123",
        "role": "student",
        "first_name": "Student",
        "last_name": "Account",
        "contact_info": "student@gmail.com",
        "gender": "Other",
        "strand": "Other",
        "payment_plan": "plan_a",
    },
]


def ensure_users_table_schema(client):
    """Ensure the users table has all required columns."""
    print("\n🔧 Ensuring users table has all required columns...")
    
    # Check if table exists by trying to query it
    try:
        client.sqlQuery("SELECT id FROM users LIMIT 1")
        table_exists = True
    except Exception:
        table_exists = False
    
    if not table_exists:
        # Create table with all columns (including strand, payment_plan)
        print("  Creating users table...")
        client.sqlExec("""
            CREATE TABLE users (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                hashed_password VARCHAR,
                role VARCHAR,
                name VARCHAR,
                active BOOLEAN,
                first_name VARCHAR,
                middle_name VARCHAR,
                last_name VARCHAR,
                contact_info VARCHAR,
                gender VARCHAR,
                strand VARCHAR,
                payment_plan VARCHAR,
                PRIMARY KEY id
            )
        """)
        print("  ✅ Users table created with all columns")
    else:
        # Check for strand and payment_plan; add via ALTER TABLE if missing (immudb supports ADD COLUMN)
        print("  Table exists. Checking schema...")
        try:
            client.sqlQuery("SELECT strand FROM users LIMIT 1")
        except Exception:
            try:
                client.sqlExec("ALTER TABLE users ADD COLUMN strand VARCHAR")
                print("  ✅ Added column 'strand' to users table")
            except Exception as e:
                print(f"  ⚠️  Could not add strand: {e}")
        try:
            client.sqlQuery("SELECT payment_plan FROM users LIMIT 1")
        except Exception:
            try:
                client.sqlExec("ALTER TABLE users ADD COLUMN payment_plan VARCHAR")
                print("  ✅ Added column 'payment_plan' to users table")
            except Exception as e:
                print(f"  ⚠️  Could not add payment_plan: {e}")
        try:
            client.sqlQuery("SELECT id, username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender, strand, payment_plan FROM users LIMIT 1")
            print("  ✅ All columns exist")
        except Exception:
            # Core columns missing - would need full recreate (strand/payment_plan already handled above)
            pass


def reset_users():
    """Delete all users and create new ones."""
    try:
        # Connect to database
        print(f"Connecting to Immudb at {DB_HOST}:{DB_PORT}...")
        client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
        client.login(DB_USER, DB_PASSWORD)
        print("✅ Connected to database")

        # Ensure table schema is correct
        ensure_users_table_schema(client)

        # Delete all existing users
        print("\n🗑️  Deleting all existing users...")
        try:
            client.sqlExec("DELETE FROM users")
            print("✅ All users deleted")
        except Exception as e:
            print(f"⚠️  Error deleting users (might be empty): {e}")

        # Create new users
        print("\n👥 Creating new user accounts...")
        for user in USERS:
            try:
                hashed_password = get_password_hash(user["password"])
                name = f"{user['first_name']} {user['last_name']}"
                
                # Escape single quotes in strings
                def escape_sql(s):
                    return str(s).replace("'", "''") if s else ""
                
                strand_val = escape_sql(user.get("strand", "") or "")
                payment_plan_val = escape_sql(user.get("payment_plan", "") or "")
                query = f"""
                    INSERT INTO users (
                        username,
                        hashed_password,
                        role,
                        name,
                        first_name,
                        middle_name,
                        last_name,
                        contact_info,
                        gender,
                        active,
                        strand,
                        payment_plan
                    )
                    VALUES (
                        '{escape_sql(user["username"])}',
                        '{escape_sql(hashed_password)}',
                        '{escape_sql(user["role"])}',
                        '{escape_sql(name)}',
                        '{escape_sql(user["first_name"])}',
                        NULL,
                        '{escape_sql(user["last_name"])}',
                        '{escape_sql(user["contact_info"])}',
                        '{escape_sql(user["gender"])}',
                        true,
                        '{strand_val}',
                        '{payment_plan_val}'
                    )
                """
                try:
                    client.sqlExec(query)
                except Exception:
                    # Fallback if strand/payment_plan columns don't exist yet
                    query_fb = f"""
                        INSERT INTO users (
                            username, hashed_password, role, name,
                            first_name, middle_name, last_name, contact_info, gender, active
                        )
                        VALUES (
                            '{escape_sql(user["username"])}', '{escape_sql(hashed_password)}',
                            '{escape_sql(user["role"])}', '{escape_sql(name)}',
                            '{escape_sql(user["first_name"])}', NULL, '{escape_sql(user["last_name"])}',
                            '{escape_sql(user["contact_info"])}', '{escape_sql(user["gender"])}', true
                        )
                    """
                    client.sqlExec(query_fb)
                print(f"  ✅ Created: {user['username']} ({user['role']})")
            except Exception as e:
                print(f"  ❌ Failed to create {user['username']}: {e}")

        print("\n✅ User reset completed successfully!")
        print("\n📋 Summary of created accounts:")
        print("-" * 60)
        for user in USERS:
            print(f"  Username: {user['username']}")
            print(f"  Password: {user['password']}")
            print(f"  Role: {user['role']}")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("  USER ACCOUNT RESET SCRIPT")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete ALL existing users!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() in ["yes", "y"]:
        reset_users()
    else:
        print("❌ Operation cancelled.")
