"""Staff payroll summary and deductions: GET (staff own or admin/payables any), PUT (admin/payables only). Salary amount derived from staff.monthly_salary."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import get_db_client
from .transactions import ensure_role

router = APIRouter(tags=["Staff Payroll"])


def _esc(s: str) -> str:
    return (s or "").replace("'", "''")


class DeductionItem(BaseModel):
    deduction_type: str
    amount: float


class StaffPayrollUpdate(BaseModel):
    salary_amount: Optional[float] = None
    deductions: Optional[List[DeductionItem]] = None


@router.get("/staff/{staff_id}/payroll", response_model=dict)
def get_staff_payroll(
    staff_id: str,
    current_username: Optional[str] = Query(None, alias="current_username"),
):
    """Get payroll summary. Salary amount is derived from staff.monthly_salary. Staff can get own; admin/payables any."""
    client = get_db_client()
    role = None
    try:
        from .transactions import get_user_role
        role = get_user_role(client, current_username or "guest")
    except Exception:
        pass
    if role == "staff" and (current_username or "").strip().lower() != (staff_id or "").strip().lower():
        raise HTTPException(status_code=403, detail="You can only view your own payroll summary")
    if role not in ("staff", "admin", "payables") and role is not None:
        raise HTTPException(status_code=403, detail="Access denied")

    sid = _esc(staff_id)
    # Salary amount derived from staff.monthly_salary (staff table)
    salary_amount = 0.0
    try:
        staff_row = client.sqlQuery(f"SELECT monthly_salary FROM staff WHERE username = '{sid}' LIMIT 1")
        if staff_row and len(staff_row[0]) > 0 and staff_row[0][0] is not None:
            salary_amount = float(staff_row[0][0])
    except Exception:
        pass
    if salary_amount <= 0:
        try:
            row = client.sqlQuery(f"SELECT salary_amount FROM staff_payroll WHERE staff_id = '{sid}' LIMIT 1")
            if row and row[0][0] is not None:
                salary_amount = int(row[0][0]) / 100.0
        except Exception:
            pass

    ded_rows = []
    try:
        ded_rows = client.sqlQuery(
            f"SELECT id, deduction_type, amount FROM staff_deductions WHERE staff_id = '{sid}' ORDER BY id"
        )
    except Exception:
        pass

    deductions = [{"id": r[0], "deduction_type": r[1] or "", "amount": (r[2] or 0) / 100.0} for r in (ded_rows or [])]
    total_deductions = sum(d["amount"] for d in deductions)
    net_pay = max(0, salary_amount - total_deductions)

    return {
        "salary_amount": salary_amount,
        "deductions": deductions,
        "net_pay": net_pay,
    }


@router.put("/staff/{staff_id}/payroll")
def update_staff_payroll(
    staff_id: str,
    payload: StaffPayrollUpdate,
    current_username: Optional[str] = Query(None, alias="current_username"),
):
    """Update payroll (deductions; optionally sync salary to staff.monthly_salary). Admin or payables only."""
    client = get_db_client()
    ensure_role(client, current_username or "guest", ["admin", "payables"])

    sid = _esc(staff_id)
    updates = []
    un = _esc(current_username or "admin")

    if payload.salary_amount is not None:
        salary_int = int(round(payload.salary_amount))
        try:
            client.sqlExec(
                f"UPDATE staff SET monthly_salary = {salary_int} WHERE username = '{sid}'"
            )
            updates.append("salary_amount")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update monthly_salary: {e}")

    if payload.deductions is not None:
        try:
            client.sqlExec(f"DELETE FROM staff_deductions WHERE staff_id = '{sid}'")
        except Exception:
            pass
        for d in payload.deductions:
            type_str = (d.deduction_type or "").strip()
            if not type_str:
                type_str = "Deduction"
            amt_cents = int(round((d.amount or 0) * 100))
            client.sqlExec(
                f"INSERT INTO staff_deductions (staff_id, deduction_type, amount) VALUES ('{sid}', '{_esc(type_str)}', {amt_cents})"
            )
        updates.append("deductions")

    return {"message": "Payroll updated", "updated": updates}
