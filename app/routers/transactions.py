from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..database import get_db_client
from ..schemas import ApprovalRequest, TransactionCreate, TransactionResponse

router = APIRouter(tags=["Transactions"])


@router.post("/transactions", response_model=TransactionResponse)
def create_transaction(txn: TransactionCreate):
    client = get_db_client()
    try:
        # Default status: Collections are Approved immediately (usually), Disbursements need Approval
        # For this system, let's say all new inputs are 'Pending' unless specified otherwise,
        # or Collections = Approved, Disbursements = Pending.
        status = "Pending"

        # Convert float to integer cents for storage to avoid float drift
        amount_cents = int(txn.amount * 100)

        query = f"""
            INSERT INTO transactions (
                created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, proof_reference
            ) VALUES (
                NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}',
                '{txn.description}', {amount_cents}, '{status}', '{txn.student_id or ""}', '{txn.proof_reference or ""}'
            ) RETURNING id, created_at, status
        """
        # Note: RETURNING might not be fully supported in all immudb-py versions via sqlQuery immediately
        # So we might execute then select max id.
        # For safety in this demo, let's do Insert then Read.

        client.sqlExec(query)

        # Fetch back the latest transaction for this user to confirm
        # This is a bit race-condition prone in high concurrency without RETURNING, but acceptable for demo.
        res = client.sqlQuery(
            f"SELECT id, created_at FROM transactions WHERE recorded_by='{txn.recorded_by}' ORDER BY id DESC LIMIT 1"
        )
        new_id = res[0][0]
        created_at = str(res[0][1])

        return {
            "id": new_id,
            "created_at": created_at,
            "recorded_by": txn.recorded_by,
            "txn_type": txn.txn_type,
            "strand": txn.strand,
            "category": txn.category,
            "description": txn.description,
            "amount": txn.amount,
            "status": status,
            "student_id": txn.student_id,
            "proof_reference": txn.proof_reference,
        }

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    student_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100
):
    """
    Fetch transactions with optional filtering.
    """
    client = get_db_client()
    try:
        query = """
            SELECT id, created_at, recorded_by, txn_type, strand, category,
                   description, amount, status, student_id, approved_by, approval_date, proof_reference
            FROM transactions
        """

        conditions = []
        if student_id:
            conditions.append(f"student_id = '{student_id}'")
        if status:
            conditions.append(f"status = '{status}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY id DESC LIMIT {limit}"

        result = client.sqlQuery(query)

        txns = []
        for row in result:
            txns.append(
                {
                    "id": row[0],
                    "created_at": str(row[1]),
                    "recorded_by": row[2],
                    "txn_type": row[3],
                    "strand": row[4],
                    "category": row[5],
                    "description": row[6],
                    "amount": row[7] / 100.0,
                    "status": row[8],
                    "student_id": row[9],
                    "approved_by": row[10],
                    "approval_date": str(row[11]) if row[11] else None,
                    "proof_reference": row[12],
                }
            )
        return txns

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transactions/{txn_id}/approve")
def approve_transaction(txn_id: int, approval: ApprovalRequest):
    """
    Approval Workflow
    """
    client = get_db_client()
    try:
        new_status = "Approved" if approval.action == "Approve" else "Rejected"

        query = f"""
            UPDATE transactions
            SET status = '{new_status}',
                approved_by = '{approval.admin_username}',
                approval_date = NOW()
            WHERE id = {txn_id}
        """
        client.sqlExec(query)
        return {"message": f"Transaction {new_status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
