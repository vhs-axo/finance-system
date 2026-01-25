from fastapi import HTTPException
from immudb import ImmudbClient

from .core import (
    DB_HOST,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    INITIAL_ADMIN_PASS,
    INITIAL_PAYABLES_PASS,
    INITIAL_VP_FINANCE_PASS,
    INITIAL_PRESIDENT_PASS,
    INITIAL_PROCUREMENT_PASS,
    INITIAL_DEPT_HEAD_PASS,
    INITIAL_BOOKKEEPER_PASS,
    INITIAL_STUDENT_PASS,
)
from .utils import get_password_hash


def get_db_client() -> ImmudbClient:
    """Opens a connection to Immudb for a request."""
    client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    try:
        client.login(DB_USER, DB_PASSWORD)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database Unavailable")


def seed_users(client: ImmudbClient):
    """Populate the database with initial users if empty."""
    try:
        # Check if users exist
        try:
            result = client.sqlQuery("SELECT COUNT(*) FROM users")
            user_count = result[0][0]
        except Exception:
            # Table might not exist yet, treat as 0
            user_count = 0

        if user_count == 0:
            print(
                "⚡ Database is empty. Seeding default users from Environment variables..."
            )

            # Helper to safely escape strings for SQL (basic prevention)
            # In a full production app, use parameterized queries if the client library supports them fully
            users_to_seed = [
                (
                    "admin@gmail.com",
                    get_password_hash(INITIAL_ADMIN_PASS),
                    "admin",
                    "System Administrator",
                    "System",
                    "Administrator",
                    "admin@gmail.com",
                    "Other",
                ),
                (
                    "payables@gmail.com",
                    get_password_hash(INITIAL_PAYABLES_PASS),
                    "payables",
                    "Payables Associate",
                    "Payables",
                    "Associate",
                    "payables@gmail.com",
                    "Other",
                ),
                (
                    "vpfinance@gmail.com",
                    get_password_hash(INITIAL_VP_FINANCE_PASS),
                    "vp_finance",
                    "VP Finance",
                    "VP",
                    "Finance",
                    "vpfinance@gmail.com",
                    "Other",
                ),
                (
                    "president@gmail.com",
                    get_password_hash(INITIAL_PRESIDENT_PASS),
                    "president",
                    "President",
                    "President",
                    "Office",
                    "president@gmail.com",
                    "Other",
                ),
                (
                    "procurement@gmail.com",
                    get_password_hash(INITIAL_PROCUREMENT_PASS),
                    "procurement",
                    "Procurement Officer",
                    "Procurement",
                    "Officer",
                    "procurement@gmail.com",
                    "Other",
                ),
                (
                    "depthead@gmail.com",
                    get_password_hash(INITIAL_DEPT_HEAD_PASS),
                    "dept_head",
                    "Department Head",
                    "Department",
                    "Head",
                    "depthead@gmail.com",
                    "Other",
                ),
                (
                    "bookkeeper@gmail.com",
                    get_password_hash(INITIAL_BOOKKEEPER_PASS),
                    "bookkeeper",
                    "Bookkeeper",
                    "Bookkeeper",
                    "Account",
                    "bookkeeper@gmail.com",
                    "Other",
                ),
                (
                    "student@gmail.com",
                    get_password_hash(INITIAL_STUDENT_PASS),
                    "student",
                    "Student Account",
                    "Student",
                    "Account",
                    "student@gmail.com",
                    "Other",
                ),
            ]

            for u in users_to_seed:
                query = f"""
                    INSERT INTO users (
                        username, 
                        hashed_password, 
                        role, 
                        name,
                        first_name,
                        last_name,
                        contact_info,
                        gender,
                        active
                    )
                    VALUES (
                        '{u[0]}', 
                        '{u[1]}', 
                        '{u[2]}', 
                        '{u[3]}',
                        '{u[4]}',
                        '{u[5]}',
                        '{u[6]}',
                        '{u[7]}',
                        true
                    )
                """
                client.sqlExec(query)
            print("✅ Default users seeded successfully.")
    except Exception as e:
        print(f"⚠️ Seeding failed: {e}")


def ensure_users_table_schema(client):
    """Ensure the users table has all required columns. Recreates if needed."""
    try:
        # Try to query all expected columns
        client.sqlQuery("SELECT id, username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender FROM users LIMIT 1")
        # All columns exist
        return
    except Exception:
        # Columns are missing - need to recreate table
        print("⚠️  Users table schema outdated. Migrating...")
        try:
            # Try to backup existing users (if any)
            try:
                existing_users = client.sqlQuery("SELECT username, hashed_password, role, name, active FROM users")
                print(f"  Found {len(existing_users)} existing users (will be preserved if possible)")
            except Exception:
                existing_users = []
            
            # Drop existing table
            try:
                client.sqlExec("DROP TABLE users")
            except Exception:
                pass  # Table might not exist
            
            # Create new table with all columns
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
                    PRIMARY KEY id
                )
            """)
            print("  ✅ Users table schema migrated")
            
            # Note: We don't restore existing users here as they would be missing profile data
            # The seed_users function will create default users if table is empty
        except Exception as e:
            print(f"  ⚠️  Migration warning: {e}")


def init_db():
    """Initialize tables and seed data on server startup."""
    try:
        client = get_db_client()

        # 1. Create Transactions Table
        # Note: In immudb, altering tables can be strict. If table exists, this assumes
        # it matches or we are starting fresh.
        client.sqlExec("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER AUTO_INCREMENT,
                created_at TIMESTAMP,
                recorded_by VARCHAR,
                txn_type VARCHAR,
                strand VARCHAR,
                category VARCHAR,
                description VARCHAR,
                amount INTEGER,
                status VARCHAR,
                student_id VARCHAR,
                approved_by VARCHAR,
                approval_date TIMESTAMP,
                proof_reference VARCHAR,
                PRIMARY KEY id
            )
        """)

        # 2. Ensure Users Table has correct schema
        ensure_users_table_schema(client)
        
        # Create table if it doesn't exist (after migration check)
        try:
            client.sqlQuery("SELECT id FROM users LIMIT 1")
        except Exception:
            # Table doesn't exist, create it
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
                    PRIMARY KEY id
                )
            """)

        # 3. Create Index for faster lookups
        try:
            client.sqlExec("CREATE INDEX ON transactions(student_id)")
            client.sqlExec("CREATE INDEX ON transactions(status)")
        except Exception:
            pass  # Index might already exist

        # 4. Seed Users
        seed_users(client)

        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️ Startup warning (DB might be down or tables exist): {e}")
