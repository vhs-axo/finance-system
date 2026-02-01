import binascii
import hashlib
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..database import get_db_client
from ..schemas import (
    AdminActionRequest,
    ApprovalRequest,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdateAdmin,
)

router = APIRouter(tags=["Transactions"])


def _esc(s: str) -> str:
    return (s or "").replace("'", "''")


def get_user_role(client, username: str):
    """Get user role and active status (role is stored directly in users: admin, payables, student, staff, etc.)."""
    try:
        un = _esc(username)
        res = client.sqlQuery(
            f"SELECT role, active FROM users WHERE username = '{un}'"
        )
        if not res or not res[0][1]:  # Not found or not active
            return None
        return res[0][0]
    except Exception:
        return None


def ensure_admin(client, username: str):
    """Raises 403 if the provided user is not an active admin."""
    role = get_user_role(client, username)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")


def ensure_role(client, username: str, allowed_roles: list):
    """Raises 403 if the provided user is not in the allowed roles."""
    role = get_user_role(client, username)
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
        )


@router.post("/transactions", response_model=TransactionResponse)
def create_transaction(txn: TransactionCreate):
    client = get_db_client()
    try:
        # Role-based permission: Only Payables Associate, Bookkeeper, Procurement, and Admin can create transactions
        allowed_roles = ["payables", "bookkeeper", "procurement", "admin"]
        ensure_role(client, txn.recorded_by, allowed_roles)
        
        # LOGIC CHANGE: Only Disbursement requires approval workflow
        if txn.txn_type == "Disbursement":
            status = "Pending"  # Needs VP Finance endorsement, then President approval
        else:
            status = "Approved"  # Collections are auto-approved

        # Convert float to integer cents for storage
        amount_cents = int(txn.amount * 100)

        query = f"""
            INSERT INTO transactions (
                created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, staff_id, proof_reference
            ) VALUES (
                NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}',
                '{txn.description}', {amount_cents}, '{status}', '{txn.student_id or ""}', '{txn.staff_id or ""}', '{txn.proof_reference or ""}'
            )
        """
        try:
            client.sqlExec(query)
        except Exception:
            query_old = f"""
                INSERT INTO transactions (
                    created_at, recorded_by, txn_type, strand, category,
                    description, amount, status, student_id, proof_reference
                ) VALUES (
                    NOW(), '{txn.recorded_by}', '{txn.txn_type}', '{txn.strand}', '{txn.category}',
                    '{txn.description}', {amount_cents}, '{status}', '{txn.student_id or ""}', '{txn.proof_reference or ""}'
                )
            """
            client.sqlExec(query_old)

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

        # If this is a Collection transaction with a student_id, update bill balances
        if txn.txn_type == "Collection" and txn.student_id:
            try:
                # Get all pending/partial bill assignments for this student
                bill_res = client.sqlQuery(f"""
                    SELECT id, amount, paid_amount
                    FROM bill_assignments
                    WHERE student_id = '{txn.student_id}' AND status IN ('Pending', 'Partial')
                    ORDER BY id ASC
                """)
                
                remaining_payment = amount_cents
                for bill_assignment in bill_res:
                    if remaining_payment <= 0:
                        break
                    
                    assignment_id = bill_assignment[0]
                    bill_amount = bill_assignment[1]
                    paid_amount = bill_assignment[2]
                    remaining_bill = bill_amount - paid_amount
                    
                    if remaining_bill > 0:
                        payment_to_apply = min(remaining_payment, remaining_bill)
                        new_paid = paid_amount + payment_to_apply
                        new_status = "Paid" if new_paid >= bill_amount else "Partial"
                        
                        client.sqlExec(f"""
                            UPDATE bill_assignments
                            SET paid_amount = {new_paid}, status = '{new_status}'
                            WHERE id = {assignment_id}
                        """)
                        
                        remaining_payment -= payment_to_apply
            except Exception as e:
                print(f"⚠️  Bill balance update warning: {e}")
                # Don't fail the transaction if bill update fails

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
            "staff_id": txn.staff_id,
            "approved_by": None,
            "approval_date": None,
            "proof_reference": txn.proof_reference,
            "tx_hash": tx_hash,
        }

    except Exception as e:
        print(f"Txn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    student_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
):
    client = get_db_client()
    try:
        conditions = []
        if student_id:
            conditions.append(f"student_id = '{_esc(student_id)}'")
        if staff_id:
            conditions.append(f"staff_id = '{_esc(staff_id)}'")
        if status:
            conditions.append(f"status = '{status}'")

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # Try with staff_id (new schema); fallback without it for old DBs
        query_with_staff = f"""
            SELECT
                id, created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, staff_id, approved_by,
                approval_date, proof_reference
            FROM transactions
            {where_clause}
            ORDER BY created_at DESC LIMIT {limit}
        """
        query_without_staff = f"""
            SELECT
                id, created_at, recorded_by, txn_type, strand, category,
                description, amount, status, student_id, approved_by,
                approval_date, proof_reference
            FROM transactions
            {where_clause}
            ORDER BY created_at DESC LIMIT {limit}
        """
        try:
            result = client.sqlQuery(query_with_staff)
            has_staff_col = True
        except Exception:
            result = client.sqlQuery(query_without_staff)
            has_staff_col = False

        txns = []
        for row in result:
            content_str = f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[7]}|{row[8]}"
            tx_hash_bytes = hashlib.sha256(content_str.encode()).digest()
            tx_hash = binascii.hexlify(tx_hash_bytes).decode("utf-8")
            if has_staff_col:
                # 0 id, 1 created_at, 2 recorded_by, 3 txn_type, 4 strand, 5 category, 6 description, 7 amount, 8 status, 9 student_id, 10 staff_id, 11 approved_by, 12 approval_date, 13 proof_reference
                txns.append({
                    "id": row[0], "created_at": str(row[1]), "recorded_by": row[2], "txn_type": row[3], "strand": row[4],
                    "category": row[5], "description": row[6], "amount": row[7] / 100.0, "status": row[8],
                    "student_id": row[9], "staff_id": row[10] if len(row) > 10 else None,
                    "approved_by": row[11] if len(row) > 11 else None, "approval_date": str(row[12]) if len(row) > 12 and row[12] else None,
                    "proof_reference": row[13] if len(row) > 13 else None, "tx_hash": tx_hash,
                })
            else:
                # 0 id, 1 created_at, 2 recorded_by, 3 txn_type, 4 strand, 5 category, 6 description, 7 amount, 8 status, 9 student_id, 10 approved_by, 11 approval_date, 12 proof_reference
                txns.append({
                    "id": row[0], "created_at": str(row[1]), "recorded_by": row[2], "txn_type": row[3], "strand": row[4],
                    "category": row[5], "description": row[6], "amount": row[7] / 100.0, "status": row[8],
                    "student_id": row[9], "staff_id": None,
                    "approved_by": row[10] if len(row) > 10 else None, "approval_date": str(row[11]) if len(row) > 11 and row[11] else None,
                    "proof_reference": row[12] if len(row) > 12 else None, "tx_hash": tx_hash,
                })
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
    Multi-level Approval Workflow:
    - VP Finance: Can endorse pending disbursements (status: "Pending" → "Endorsed")
    - President: Has final say - can approve/reject both Pending and Endorsed disbursements
    - Admin: Can approve/reject any transaction
    """
    client = get_db_client()
    try:
        # Get current transaction status
        txn_res = client.sqlQuery(
            f"SELECT txn_type, status FROM transactions WHERE id = {txn_id}"
        )
        if not txn_res:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        txn_type = txn_res[0][0]
        current_status = txn_res[0][1]
        user_role = get_user_role(client, approval.admin_username)
        
        if not user_role:
            raise HTTPException(status_code=403, detail="Invalid user")
        
        # Determine new status based on role and action
        if approval.action == "Reject":
            new_status = "Rejected"
        elif user_role == "admin":
            # Admin can directly approve/reject anything
            new_status = "Approved" if approval.action == "Approve" else "Rejected"
        elif user_role == "vp_finance":
            # VP Finance can endorse disbursements (marks as endorsed, but doesn't approve)
            if txn_type == "Disbursement" and current_status == "Pending":
                new_status = "Endorsed" if approval.action == "Approve" else "Rejected"
            else:
                raise HTTPException(
                    status_code=403, 
                    detail="VP Finance can only endorse pending disbursements"
                )
        elif user_role == "president":
            # President has final say - can approve/reject both Pending and Endorsed disbursements
            if txn_type == "Disbursement" and current_status in ["Pending", "Endorsed"]:
                new_status = "Approved" if approval.action == "Approve" else "Rejected"
            else:
                raise HTTPException(
                    status_code=403,
                    detail="President can only approve/reject disbursements"
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to approve transactions"
            )

        query = f"""
            UPDATE transactions
            SET status = '{new_status}',
                approved_by = '{approval.admin_username}',
                approval_date = NOW()
            WHERE id = {txn_id}
        """
        client.sqlExec(query)

        return {"message": f"Transaction {new_status}"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Approval Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transactions/{txn_id}")
def admin_update_transaction(txn_id: int, payload: TransactionUpdateAdmin):
    """
    Admin-only endpoint to edit ledger entries.
    """
    client = get_db_client()
    ensure_admin(client, payload.admin_username)

    updates = []
    if payload.txn_type:
        updates.append(f"txn_type = '{payload.txn_type}'")
    if payload.strand:
        updates.append(f"strand = '{payload.strand}'")
    if payload.category:
        updates.append(f"category = '{payload.category}'")
    if payload.description is not None:
        updates.append(f"description = '{payload.description}'")
    if payload.amount is not None:
        updates.append(f"amount = {int(payload.amount * 100)}")
    if payload.status:
        updates.append(f"status = '{payload.status}'")
    if payload.student_id is not None:
        updates.append(f"student_id = '{payload.student_id}'")
    if payload.staff_id is not None:
        updates.append(f"staff_id = '{_esc(payload.staff_id)}'")
    if payload.proof_reference is not None:
        updates.append(f"proof_reference = '{payload.proof_reference}'")

    if not updates:
        return {"message": "No changes requested"}

    set_clause = ", ".join(updates)

    try:
        client.sqlExec(f"UPDATE transactions SET {set_clause} WHERE id = {txn_id}")
        return {"message": "Transaction updated"}
    except Exception as e:
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transactions/{txn_id}/void")
def admin_void_transaction(txn_id: int, payload: AdminActionRequest):
    """
    Admin-only endpoint to void (soft-delete) ledger entries.
    Preserves record for audit by setting status and stamping admin + date.
    """
    client = get_db_client()
    ensure_admin(client, payload.admin_username)
    try:
        client.sqlExec(
            f"""
            UPDATE transactions
            SET status = 'Voided',
                approved_by = '{payload.admin_username}',
                approval_date = NOW()
            WHERE id = {txn_id}
            """
        )
        return {"message": "Transaction voided"}
    except Exception as e:
        print(f"Void Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transactions/{txn_id}/acknowledge")
def acknowledge_transaction(txn_id: int, payload: AdminActionRequest):
    """
    Department Head endpoint to acknowledge receipt of payment for departmental requests.
    """
    client = get_db_client()
    user_role = get_user_role(client, payload.admin_username)
    
    if user_role != "dept_head":
        raise HTTPException(
            status_code=403,
            detail="Only Department Head can acknowledge receipt of payments"
        )
    
    try:
        # Get transaction to verify it's a disbursement
        txn_res = client.sqlQuery(
            f"SELECT txn_type, status FROM transactions WHERE id = {txn_id}"
        )
        if not txn_res:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        txn_type = txn_res[0][0]
        if txn_type != "Disbursement":
            raise HTTPException(
                status_code=400,
                detail="Only disbursements can be acknowledged"
            )
        
        # Add acknowledgment note to description
        # Get current description first
        desc_res = client.sqlQuery(
            f"SELECT description FROM transactions WHERE id = {txn_id}"
        )
        current_desc = desc_res[0][0] if desc_res and desc_res[0][0] else ""
        ack_note = f" [Acknowledged by {payload.admin_username} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
        new_desc = current_desc + ack_note
        
        client.sqlExec(
            f"""
            UPDATE transactions
            SET description = '{new_desc.replace("'", "''")}'
            WHERE id = {txn_id}
            """
        )
        return {"message": "Payment acknowledged"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Acknowledgment Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
