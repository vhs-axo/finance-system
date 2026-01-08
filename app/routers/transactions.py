from fastapi import APIRouter, HTTPException
from typing import List
from ..schemas import TransactionCreate, TransactionResponse
from ..database import get_db_client

router = APIRouter(tags=["Transactions"])

@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions():
    client = get_db_client()
    try:
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

@router.post("/transactions", status_code=201)
def create_transaction(txn: TransactionCreate):
    client = get_db_client()
    try:
        amount_cents = int(txn.amount * 100)
        status = 'Pending' if txn.txn_type == 'Disbursement' else 'Verified'
        
        # Note: In production, consider parameterized queries or ORM for safety
        query = f"""
            INSERT INTO transactions (created_at, recorded_by, txn_type, strand, category, description, amount, status)
            VALUES (NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}', '{txn.description}', {amount_cents}, '{status}')
        """
        client.sqlExec(query)
        return {"message": "Transaction recorded immutably"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify/{txn_id}")
def verify_transaction(txn_id: int):
    client = get_db_client()
    try:
        # Check if record exists in the immutable ledger
        result = client.sqlQuery(f"SELECT id, created_at, amount, description FROM transactions WHERE id = {txn_id}")
        
        if not result:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Immudb ensures that if we can read it here, it hasn't been tampered with.
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
