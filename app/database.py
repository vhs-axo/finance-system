from immudb import ImmudbClient
from fastapi import HTTPException
from .core import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

def get_db_client():
    """Opens a connection to Immudb for a request."""
    client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    try:
        client.login(DB_USER, DB_PASSWORD)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database Unavailable")

def init_db():
    """Initialize the table on server startup."""
    try:
        client = get_db_client()
        
        # Create table if not exists
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
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️ Startup warning (table might exist or DB down): {e}")
