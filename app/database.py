from fastapi import HTTPException
from immudb import ImmudbClient

from .core import (
    DB_HOST,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    INITIAL_ADMIN_PASS,
    INITIAL_BOOKKEEPER_PASS,
    INITIAL_DEPT_HEAD_PASS,
    INITIAL_PAYABLES_PASS,
    INITIAL_PRESIDENT_PASS,
    INITIAL_PROCUREMENT_PASS,
    INITIAL_STUDENT_PASS,
    INITIAL_VP_FINANCE_PASS,
)
from .utils import get_password_hash

# Each of these has its own table with same schema: username, first_name, middle_name, last_name, gender, contact_information
ROLE_TABLES = ["admin", "payables", "bookkeeper", "vp_finance", "president", "procurement", "dept_head", "it"]


def get_db_client() -> ImmudbClient:
    """Opens a connection to Immudb for a request."""
    client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    try:
        client.login(DB_USER, DB_PASSWORD)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database Unavailable")


def _role_table_schema(table_name: str) -> str:
    """Same schema for all role tables (admin, payables, etc.)."""
    return f"""
            CREATE TABLE {table_name} (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                first_name VARCHAR,
                middle_name VARCHAR,
                last_name VARCHAR,
                gender VARCHAR,
                contact_information VARCHAR,
                PRIMARY KEY id
            )
        """


def _ensure_new_user_tables(client: ImmudbClient):
    """
    - users: id, username, hashed_password, role (student|staff|admin|payables|...), active
    - students, staff: as before
    - admin, payables, bookkeeper, vp_finance, president, procurement, dept_head, it: each own table, same columns
    """
    # Check if old users table exists (has 'name' column)
    try:
        client.sqlQuery("SELECT id, username, name FROM users LIMIT 1")
        try:
            client.sqlExec("DROP TABLE users")
        except Exception:
            pass
    except Exception:
        pass

    # Create users table if not exists
    try:
        client.sqlQuery("SELECT id, username, role, active FROM users LIMIT 1")
    except Exception:
        client.sqlExec("""
            CREATE TABLE users (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                hashed_password VARCHAR,
                role VARCHAR,
                active BOOLEAN,
                PRIMARY KEY id
            )
        """)
        print("  ✅ Created users table")

    # Create students table if not exists
    try:
        client.sqlQuery("SELECT id FROM students LIMIT 1")
    except Exception:
        client.sqlExec("""
            CREATE TABLE students (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                first_name VARCHAR,
                middle_name VARCHAR,
                last_name VARCHAR,
                gender VARCHAR,
                strand VARCHAR,
                section VARCHAR,
                payment_plan VARCHAR,
                PRIMARY KEY id
            )
        """)
        print("  ✅ Created students table")

    # Create staff table if not exists
    try:
        client.sqlQuery("SELECT id FROM staff LIMIT 1")
    except Exception:
        client.sqlExec("""
            CREATE TABLE staff (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                first_name VARCHAR,
                middle_name VARCHAR,
                last_name VARCHAR,
                gender VARCHAR,
                position VARCHAR,
                department VARCHAR,
                date_hired VARCHAR,
                status VARCHAR,
                monthly_salary INTEGER,
                PRIMARY KEY id
            )
        """)
        print("  ✅ Created staff table")

    # Drop old general table if it exists (migration)
    try:
        client.sqlExec("DROP TABLE general")
        print("  ✅ Dropped old general table")
    except Exception:
        pass

    # Create one table per role: admin, payables, bookkeeper, vp_finance, president, procurement, dept_head, it
    for table_name in ROLE_TABLES:
        try:
            client.sqlQuery(f"SELECT id FROM {table_name} LIMIT 1")
        except Exception:
            client.sqlExec(_role_table_schema(table_name))
            print(f"  ✅ Created {table_name} table")


def seed_users(client: ImmudbClient):
    """Populate the database with initial users if empty (users + role tables)."""
    try:
        try:
            result = client.sqlQuery("SELECT COUNT(*) FROM users")
            user_count = result[0][0]
        except Exception:
            user_count = 0

        if user_count == 0:
            print("⚡ Database is empty. Seeding default users (users + role tables)...")
            # Role-specific users: each gets role=admin/payables/... and a row in that table
            role_seed = [
                ("admin@gmail.com", get_password_hash(INITIAL_ADMIN_PASS), "admin", "System", "", "Administrator", "Other", "admin@gmail.com"),
                ("payables@gmail.com", get_password_hash(INITIAL_PAYABLES_PASS), "payables", "Payables", "", "Associate", "Other", "payables@gmail.com"),
                ("vpfinance@gmail.com", get_password_hash(INITIAL_VP_FINANCE_PASS), "vp_finance", "VP", "", "Finance", "Other", "vpfinance@gmail.com"),
                ("president@gmail.com", get_password_hash(INITIAL_PRESIDENT_PASS), "president", "President", "", "Office", "Other", "president@gmail.com"),
                ("procurement@gmail.com", get_password_hash(INITIAL_PROCUREMENT_PASS), "procurement", "Procurement", "", "Officer", "Other", "procurement@gmail.com"),
                ("depthead@gmail.com", get_password_hash(INITIAL_DEPT_HEAD_PASS), "dept_head", "Department", "", "Head", "Other", "depthead@gmail.com"),
                ("bookkeeper@gmail.com", get_password_hash(INITIAL_BOOKKEEPER_PASS), "bookkeeper", "Bookkeeper", "", "Account", "Other", "bookkeeper@gmail.com"),
            ]
            def _e(s):
                return (s or "").replace("'", "''")
            for username, hashed_pw, role, fn, mn, ln, gender, contact in role_seed:
                client.sqlExec(
                    f"INSERT INTO users (username, hashed_password, role, active) "
                    f"VALUES ('{_e(username)}', '{_e(hashed_pw)}', '{role}', true)"
                )
                client.sqlExec(
                    f"INSERT INTO {role} (username, first_name, middle_name, last_name, gender, contact_information) "
                    f"VALUES ('{_e(username)}', '{_e(fn)}', '{_e(mn)}', '{_e(ln)}', '{_e(gender)}', '{_e(contact)}')"
                )
            # One student
            student_pw = get_password_hash(INITIAL_STUDENT_PASS).replace("'", "''")
            client.sqlExec(
                f"INSERT INTO users (username, hashed_password, role, active) "
                f"VALUES ('student@gmail.com', '{student_pw}', 'student', true)"
            )
            client.sqlExec("""
                INSERT INTO students (username, first_name, middle_name, last_name, gender, strand, section, payment_plan)
                VALUES ('student@gmail.com', 'Student', '', 'Account', 'Other', 'Other', '', 'plan_a')
            """)
            print("✅ Default users seeded successfully.")
    except Exception as e:
        print(f"⚠️ Seeding failed: {e}")


def init_db():
    """Initialize tables and seed data on server startup."""
    try:
        client = get_db_client()

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
                staff_id VARCHAR,
                approved_by VARCHAR,
                approval_date TIMESTAMP,
                proof_reference VARCHAR,
                PRIMARY KEY id
            )
        """)

        _ensure_new_user_tables(client)

        try:
            client.sqlQuery("SELECT id FROM bills LIMIT 1")
        except Exception:
            client.sqlExec("""
                CREATE TABLE bills (
                    id INTEGER AUTO_INCREMENT,
                    created_at TIMESTAMP,
                    bill_type VARCHAR,
                    description VARCHAR,
                    total_amount INTEGER,
                    created_by VARCHAR,
                    PRIMARY KEY id
                )
            """)

        try:
            client.sqlQuery("SELECT id FROM bill_assignments LIMIT 1")
        except Exception:
            client.sqlExec("""
                CREATE TABLE bill_assignments (
                    id INTEGER AUTO_INCREMENT,
                    bill_id INTEGER,
                    student_id VARCHAR,
                    amount INTEGER,
                    paid_amount INTEGER,
                    status VARCHAR,
                    PRIMARY KEY id
                )
            """)

        try:
            client.sqlQuery("SELECT id FROM financial_allocations LIMIT 1")
        except Exception:
            client.sqlExec("""
                CREATE TABLE financial_allocations (
                    id INTEGER AUTO_INCREMENT,
                    name VARCHAR,
                    amount INTEGER,
                    PRIMARY KEY id
                )
            """)

        try:
            client.sqlQuery("SELECT id FROM staff_payroll LIMIT 1")
        except Exception:
            client.sqlExec("""
                CREATE TABLE staff_payroll (
                    id INTEGER AUTO_INCREMENT,
                    staff_id VARCHAR,
                    salary_amount INTEGER,
                    updated_at TIMESTAMP,
                    updated_by VARCHAR,
                    PRIMARY KEY id
                )
            """)
            client.sqlExec("CREATE INDEX ON staff_payroll(staff_id)")
            print("  ✅ Created staff_payroll table")
        try:
            client.sqlQuery("SELECT id FROM staff_deductions LIMIT 1")
        except Exception:
            client.sqlExec("""
                CREATE TABLE staff_deductions (
                    id INTEGER AUTO_INCREMENT,
                    staff_id VARCHAR,
                    deduction_type VARCHAR,
                    amount INTEGER,
                    PRIMARY KEY id
                )
            """)
            client.sqlExec("CREATE INDEX ON staff_deductions(staff_id)")
            print("  ✅ Created staff_deductions table")

        try:
            client.sqlExec("CREATE INDEX ON transactions(student_id)")
            client.sqlExec("CREATE INDEX ON transactions(staff_id)")
            client.sqlExec("CREATE INDEX ON transactions(status)")
            client.sqlExec("CREATE INDEX ON bill_assignments(student_id)")
        except Exception:
            pass
        # Migration: add staff_id if table existed without it
        try:
            client.sqlQuery("SELECT staff_id FROM transactions LIMIT 1")
        except Exception:
            try:
                client.sqlExec("ALTER TABLE transactions ADD COLUMN staff_id VARCHAR")
                print("  ✅ Added staff_id to transactions")
            except Exception:
                pass

        seed_users(client)
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️ Startup warning (DB might be down or tables exist): {e}")
