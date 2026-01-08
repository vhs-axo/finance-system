from immudb import ImmudbClient
from fastapi import HTTPException
from .core import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
    INITIAL_ADMIN_PASS, INITIAL_STAFF_PASS, INITIAL_AUDITOR_PASS
)
from .utils import get_password_hash

def get_db_client():
    """Opens a connection to Immudb for a request."""
    client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    try:
        client.login(DB_USER, DB_PASSWORD)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database Unavailable")

def seed_users(client):
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
            print("⚡ Database is empty. Seeding default users from Environment variables...")
            
            # Helper to safely escape strings for SQL (basic prevention)
            # In a full production app, use parameterized queries if the client library supports them fully
            users_to_seed = [
                ("admin", get_password_hash(INITIAL_ADMIN_PASS), "admin", "Principal Skinner"),
                ("staff", get_password_hash(INITIAL_STAFF_PASS), "staff", "Finance Clerk"),
                ("auditor", get_password_hash(INITIAL_AUDITOR_PASS), "auditor", "External Auditor")
            ]
            
            for u in users_to_seed:
                query = f"""
                    INSERT INTO users (username, hashed_password, role, name, active)
                    VALUES ('{u[0]}', '{u[1]}', '{u[2]}', '{u[3]}', true)
                """
                client.sqlExec(query)
            print("✅ Default users seeded successfully.")
    except Exception as e:
        print(f"⚠️ Seeding failed: {e}")

def init_db():
    """Initialize tables and seed data on server startup."""
    try:
        client = get_db_client()
        
        # 1. Create Transactions Table
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
                PRIMARY KEY id
            )
        """)
        
        # 2. Create Users Table
        client.sqlExec("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER AUTO_INCREMENT,
                username VARCHAR,
                hashed_password VARCHAR,
                role VARCHAR,
                name VARCHAR,
                active BOOLEAN,
                PRIMARY KEY id
            )
        """)
        
        # 3. Seed Users
        seed_users(client)
        
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️ Startup warning (DB might be down or tables exist): {e}")
