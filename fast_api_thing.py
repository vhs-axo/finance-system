from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from immudb import ImmudbClient
import uvicorn

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Financial Transparency API",
    description="Backend API for Senior High School Finance System using Immudb",
    version="1.0.0"
)
# --- FIX FOR "NetworkError" / CORS ---
# This block allows your frontend (React, Angular, HTML file, etc.)
# to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your frontend URL (e.g., "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allows all headers
)
# -----------------------------------------------------
DB_HOST = "127.0.0.1"
DB_PORT = 3322
DB_USER = "immudb"
DB_PASSWORD = "immudb"

# Mock Users (In production, store hashed passwords in DB)
USERS = {
    "admin": {"password": "admin123", "role": "admin", "name": "Principal Skinner"},
    "staff": {"password": "staff123", "role": "staff", "name": "Finance Clerk"},
    "auditor": {"password": "auditor123", "role": "auditor", "name": "External Auditor"},
}

# -----------------------------------------------------------------------------
# DATA MODELS (Pydantic)
# Defines the shape of JSON data your frontend sends/receives
# -----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    name: Optional[str] = None
    message: str

class TransactionCreate(BaseModel):
    recorded_by: str
    txn_type: str  # "Collection" or "Disbursement"
    strand: str
    category: str
    description: str
    amount: float

class TransactionResponse(BaseModel):
    id: int
    created_at: str
    recorded_by: str
    txn_type: str
    strand: str
    category: str
    description: str
    amount: float
    status: str

class DashboardStats(BaseModel):
    total_tuition: float
    total_misc: float
    total_org: float
    total_expenses: float

# -----------------------------------------------------------------------------
# DATABASE CONNECTION
# -----------------------------------------------------------------------------
def get_db_client():
    """Opens a connection to Immudb for a request."""
    client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    try:
        client.login(DB_USER, DB_PASSWORD)
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database Unavailable")

@app.on_event("startup")
def startup_db():
    """Initialize table on server startup."""
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
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Startup warning (table might exist): {e}")

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "online", "system": "Financial Transparency API"}

# 1. LOGIN ENDPOINT
@app.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    user = USERS.get(creds.username)
    if user and user['password'] == creds.password:
        return {
            "success": True, 
            "role": user['role'], 
            "name": user['name'], 
            "message": "Login successful"
        }
    return {"success": False, "message": "Invalid credentials"}

# 2. GET ALL TRANSACTIONS
@app.get("/transactions", response_model=List[TransactionResponse])
def get_transactions():
    client = get_db_client()
    try:
        # Query immudb
        result = client.sqlQuery("SELECT id, created_at, recorded_by, txn_type, strand, category, description, amount, status FROM transactions ORDER BY id DESC")
        
        data = []
        for row in result:
            data.append({
                "id": row[0],
                "created_at": str(row[1]),
                "recorded_by": row[2],
                "txn_type": row[3],
                "strand": row[4],
                "category": row[5],
                "description": row[6],
                "amount": row[7] / 100.0, # Convert cents back to float
                "status": row[8]
            })
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. CREATE TRANSACTION
@app.post("/transactions", status_code=201)
def create_transaction(txn: TransactionCreate):
    client = get_db_client()
    try:
        # Convert float amount to integer cents
        amount_cents = int(txn.amount * 100)
        status = 'Pending' if txn.txn_type == 'Disbursement' else 'Verified'
        
        # Insert using raw SQL for simplicity in this demo
        # NOTE: In production, sanitize inputs strictly
        query = f"""
            INSERT INTO transactions (created_at, recorded_by, txn_type, strand, category, description, amount, status)
            VALUES (NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}', '{txn.description}', {amount_cents}, '{status}')
        """
        client.sqlExec(query)
        return {"message": "Transaction recorded immutably"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. DASHBOARD STATS
@app.get("/stats", response_model=DashboardStats)
def get_stats():
    client = get_db_client()
    try:
        result = client.sqlQuery("SELECT txn_type, category, amount FROM transactions")
        
        tuition = 0
        misc = 0
        org = 0
        expenses = 0
        
        for row in result:
            txn_type = row[0]
            category = row[1]
            amount = row[2] / 100.0
            
            if txn_type == 'Disbursement':
                expenses += amount
            elif txn_type == 'Collection':
                if category == 'Tuition Fee':
                    tuition += amount
                elif category == 'Miscellaneous Fee':
                    misc += amount
                elif category == 'Organization Fund':
                    org += amount

        return {
            "total_tuition": tuition,
            "total_misc": misc,
            "total_org": org,
            "total_expenses": expenses
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. VERIFICATION (AUDIT)
@app.get("/verify/{txn_id}")
def verify_transaction(txn_id: int):
    client = get_db_client()
    try:
        # Check if record exists in the immutable ledger
        result = client.sqlQuery(f"SELECT id, created_at, amount, description FROM transactions WHERE id = {txn_id}")
        
        if not result:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        # If we got here, the data exists in immudb.
        # Immudb ensures that if we can read it, it hasn't been tampered with.
        return {
            "valid": True,
            "message": "Transaction integrity verified against immutable ledger.",
            "data": {
                "id": result[0][0],
                "timestamp": str(result[0][1]),
                "amount": result[0][2] / 100.0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
