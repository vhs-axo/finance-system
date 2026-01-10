import binascii
import hashlib
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..database import get_db_client
from ..schemas import ApprovalRequest, TransactionCreate, TransactionResponse

router = APIRouter(tags=["Transactions"])


@router.post("/transactions", response_model=TransactionResponse)
def create_transaction(txn: TransactionCreate):
    client = get_db_client()
    try:
        # LOGIC CHANGE: Only Disbursement requires approval
        if txn.txn_type == "Disbursement":
            status = "Pending"
        else:
            status = "Approved"

        # Convert float to integer cents for storage
        amount_cents = int(txn.amount * 100)

        query = f"""
            INSERT INTO transactions (
                created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, proof_reference
            ) VALUES (
                NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}',
                '{txn.description}', {amount_cents}, '{status}', '{txn.student_id or ""}', '{txn.proof_reference or ""}'
            )
        """

        client.sqlExec(query)

        # Fetch back the latest transaction for this user to get the generated ID
        res = client.sqlQuery(
            f"SELECT id, created_at FROM transactions WHERE recorded_by='{txn.recorded_by}' ORDER BY id DESC LIMIT 1"
        )

        if not res:
            raise HTTPException(
                status_code=500,
                detail="Transaction created but could not be retrieved",
            )

        new_id = res[0][0]
        created_at = res[0][1]

        # --- IMMUTABLE LEDGER ENTRY (verifiedSet) ---
        # We explicitly store critical data in the Key-Value store using verifiedSet.
        # This ensures a cryptographic proof is generated and verified for this specific entry.
        try:
            audit_key = f"txn:{new_id}".encode("utf-8")
            audit_payload = {
                "id": new_id,
                "recorded_by": txn.recorded_by,
                "amount": txn.amount,
                "type": txn.txn_type,
                "timestamp": str(created_at),
                "desc": txn.description,
                "initial_status": status,
            }
            audit_value = json.dumps(audit_payload).encode("utf-8")

            # verifiedSet ensures the data is committed and consistency is proved
            client.verifiedSet(audit_key, audit_value)

            # Use a visual indicator for the hash in UI
            tx_hash = f"VERIFIED-KEY-{new_id}"
        except Exception as e:
            print(f"⚠️ Verification Storage Warning: {e}")
            tx_hash = f"PENDING-{new_id}"

        return {
            "id": new_id,
            "created_at": str(created_at),
            "recorded_by": txn.recorded_by,
            "txn_type": txn.txn_type,
            "strand": txn.strand,
            "category": txn.category,
            "description": txn.description,
            "amount": txn.amount,
            "status": status,
            "student_id": txn.student_id,
            "proof_reference": txn.proof_reference,
            "tx_hash": tx_hash,
        }

    except Exception as e:
        print(f"Txn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    student_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100
):
    client = get_db_client()
    try:
        # Build conditions
        conditions = []
        if student_id:
            conditions.append(f"student_id = '{student_id}'")
        if status:
            conditions.append(f"status = '{status}'")

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                id, created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, approved_by,
                approval_date, proof_reference
            FROM transactions
            {where_clause}
            ORDER BY created_at DESC LIMIT {limit}
        """
        result = client.sqlQuery(query)

        txns = []
        for row in result:
            # We generate a deterministic SHA-256 hash of the content for display
            content_str = f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[7]}|{row[8]}"
            tx_hash_bytes = hashlib.sha256(content_str.encode()).digest()
            tx_hash = binascii.hexlify(tx_hash_bytes).decode("utf-8")

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
                    "tx_hash": tx_hash,
                }
            )
        return txns

    except Exception as e:
        print(f"Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{txn_id}")
def verify_transaction_integrity(txn_id: int):
    """
    Uses verifiedGet to strictly verify the transaction against the immutable ledger.
    """
    client = get_db_client()
    try:
        key = f"txn:{txn_id}".encode("utf-8")

        # verifiedGet: Retrieves value AND verifies the cryptographic proof
        # If the proof is invalid or data tampered, this method raises an exception.
        result = client.verifiedGet(key)

        # result.value contains the bytes we stored
        verified_data = json.loads(result.value.decode("utf-8"))

        return {
            "verified": True,
            "status": "Integrity Confirmed",
            "ledger_payload": verified_data,
            "message": "Cryptographic proof matches database root.",
        }
    except Exception as e:
        # This occurs if the key doesn't exist OR if verification fails (tampering detected)
        raise HTTPException(status_code=400, detail=f"Verification Failed: {str(e)}")


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
        print(f"Approval Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
