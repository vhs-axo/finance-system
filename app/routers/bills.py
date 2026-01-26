from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_db_client
from ..routers.transactions import ensure_role

router = APIRouter(tags=["Bills"])


class BillCreate(BaseModel):
    bill_type: str  # "Tuition" or "College Funds"
    description: str
    total_amount: float
    created_by: str
    student_ids: List[str]  # List of student IDs to assign this bill to


class BillAssignmentResponse(BaseModel):
    id: int
    bill_id: int
    student_id: str
    amount: float
    paid_amount: float
    status: str
    bill_type: str | None = None


class BillResponse(BaseModel):
    id: int
    created_at: str
    bill_type: str
    description: str
    total_amount: float
    created_by: str
    assignments: List[BillAssignmentResponse]


@router.post("/bills", response_model=BillResponse)
def create_bill(bill: BillCreate):
    """Create a bill and assign it to students. Only Payables Associate can create bills."""
    client = get_db_client()
    try:
        ensure_role(client, bill.created_by, ["payables", "admin"])
        
        # Convert amount to cents
        amount_cents = int(bill.total_amount * 100)
        per_student_cents = amount_cents // len(bill.student_ids) if bill.student_ids else 0
        
        # Insert bill
        query = f"""
            INSERT INTO bills (created_at, bill_type, description, total_amount, created_by)
            VALUES (NOW(), '{bill.bill_type}', '{bill.description}', {amount_cents}, '{bill.created_by}')
        """
        client.sqlExec(query)
        
        # Get the created bill ID
        res = client.sqlQuery("SELECT id, created_at FROM bills ORDER BY id DESC LIMIT 1")
        if not res:
            raise HTTPException(status_code=500, detail="Bill created but could not be retrieved")
        
        bill_id = res[0][0]
        created_at = res[0][1]
        
        # Create assignments for each student
        assignments = []
        for student_id in bill.student_ids:
            assign_query = f"""
                INSERT INTO bill_assignments (bill_id, student_id, amount, paid_amount, status)
                VALUES ({bill_id}, '{student_id}', {per_student_cents}, 0, 'Pending')
            """
            client.sqlExec(assign_query)
            
            # Get assignment ID
            assign_res = client.sqlQuery(f"SELECT id FROM bill_assignments WHERE bill_id={bill_id} AND student_id='{student_id}' ORDER BY id DESC LIMIT 1")
            if assign_res:
                assignments.append({
                    "id": assign_res[0][0],
                    "bill_id": bill_id,
                    "student_id": student_id,
                    "amount": per_student_cents / 100.0,
                    "paid_amount": 0.0,
                    "status": "Pending"
                })
        
        return {
            "id": bill_id,
            "created_at": str(created_at),
            "bill_type": bill.bill_type,
            "description": bill.description,
            "total_amount": bill.total_amount,
            "created_by": bill.created_by,
            "assignments": assignments
        }
    except Exception as e:
        print(f"Bill creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bills", response_model=List[BillResponse])
def get_bills():
    """Get all bills. Only Payables Associate and Admin can view."""
    client = get_db_client()
    try:
        res = client.sqlQuery("SELECT id, created_at, bill_type, description, total_amount, created_by FROM bills ORDER BY id DESC")
        
        bills = []
        for row in res:
            bill_id = row[0]
            # Get assignments for this bill
            assign_res = client.sqlQuery(f"""
                SELECT id, bill_id, student_id, amount, paid_amount, status
                FROM bill_assignments WHERE bill_id = {bill_id}
            """)
            
            assignments = []
            for a in assign_res:
                assignments.append({
                    "id": a[0],
                    "bill_id": a[1],
                    "student_id": a[2],
                    "amount": a[3] / 100.0,
                    "paid_amount": a[4] / 100.0,
                    "status": a[5]
                })
            
            bills.append({
                "id": row[0],
                "created_at": str(row[1]),
                "bill_type": row[2],
                "description": row[3],
                "total_amount": row[4] / 100.0,
                "created_by": row[5],
                "assignments": assignments
            })
        
        return bills
    except Exception as e:
        print(f"Get bills error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bills/student/{student_id}", response_model=List[BillAssignmentResponse])
def get_student_bills(student_id: str):
    """Get all bills for a specific student."""
    client = get_db_client()
    try:
        res = client.sqlQuery(f"""
            SELECT ba.id, ba.bill_id, ba.student_id, ba.amount, ba.paid_amount, ba.status, b.bill_type
            FROM bill_assignments ba
            LEFT JOIN bills b ON ba.bill_id = b.id
            WHERE ba.student_id = '{student_id}'
        """)
        
        assignments = []
        for row in res:
            assignments.append({
                "id": row[0],
                "bill_id": row[1],
                "student_id": row[2],
                "amount": row[3] / 100.0,
                "paid_amount": row[4] / 100.0,
                "status": row[5],
                "bill_type": row[6] if len(row) > 6 else None
            })
        
        return assignments
    except Exception as e:
        print(f"Get student bills error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bills/assignments/{assignment_id}/update-payment")
def update_payment(assignment_id: int, payment_amount: float):
    """Update payment amount for a bill assignment. Called when a student makes a payment."""
    client = get_db_client()
    try:
        # Get current assignment
        res = client.sqlQuery(f"SELECT amount, paid_amount FROM bill_assignments WHERE id = {assignment_id}")
        if not res:
            raise HTTPException(status_code=404, detail="Bill assignment not found")
        
        current_amount = res[0][0]
        current_paid = res[0][1]
        payment_cents = int(payment_amount * 100)
        new_paid = current_paid + payment_cents
        
        # Update paid amount
        status = "Paid" if new_paid >= current_amount else "Partial"
        
        client.sqlExec(f"""
            UPDATE bill_assignments
            SET paid_amount = {new_paid}, status = '{status}'
            WHERE id = {assignment_id}
        """)
        
        return {"success": True, "new_paid_amount": new_paid / 100.0, "status": status}
    except Exception as e:
        print(f"Update payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
