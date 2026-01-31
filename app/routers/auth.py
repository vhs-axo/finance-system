from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..database import get_db_client
from ..schemas import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
)
from ..utils import get_password_hash, verify_password

router = APIRouter(tags=["Authentication & Users"])


@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    client = get_db_client()
    try:
        # Secure query parameter binding is recommended in prod, f-string used for demo
        try:
            query = f"SELECT hashed_password, role, name, active, first_name, last_name, strand, payment_plan FROM users WHERE username = '{creds.username}'"
            result = client.sqlQuery(query)
        except Exception:
            query = f"SELECT hashed_password, role, name, active, first_name, last_name FROM users WHERE username = '{creds.username}'"
            result = client.sqlQuery(query)

        if not result:
            return {"success": False, "message": "User not found"}

        stored_hash = result[0][0]
        role = result[0][1]
        name = result[0][2]
        is_active = result[0][3]
        first_name = result[0][4] if len(result[0]) > 4 else None
        last_name = result[0][5] if len(result[0]) > 5 else None
        strand = result[0][6] if len(result[0]) > 6 else None
        payment_plan = result[0][7] if len(result[0]) > 7 else None

        if not is_active:
            return {"success": False, "message": "Account is disabled"}

        if verify_password(creds.password, stored_hash):
            # Use first_name + last_name if available, otherwise fall back to name
            display_name = name
            if first_name and last_name:
                display_name = f"{first_name} {last_name}"
            elif first_name:
                display_name = first_name
            elif last_name:
                display_name = last_name

            return {
                "success": True,
                "role": role,
                "name": display_name,
                "first_name": first_name,
                "last_name": last_name,
                "strand": strand,
                "payment_plan": payment_plan,
                "message": "Login successful",
            }
        else:
            return {"success": False, "message": "Invalid password"}

    except Exception as e:
        print(f"Login Error: {e}")
        return {"success": False, "message": "Login failed"}


# --- USER MANAGEMENT (Missing Feature #1) ---


@router.get("/users", response_model=List[UserResponse])
def get_users():
    """List all users (For IT/Admin)."""
    client = get_db_client()
    try:
        # Try to include strand and payment_plan if columns exist
        try:
            result = client.sqlQuery(
                "SELECT username, role, name, active, first_name, middle_name, last_name, contact_info, gender, strand, payment_plan FROM users"
            )
        except Exception:
            try:
                result = client.sqlQuery(
                    "SELECT username, role, name, active, first_name, middle_name, last_name, contact_info, gender, strand FROM users"
                )
            except Exception:
                result = client.sqlQuery(
                    "SELECT username, role, name, active, first_name, middle_name, last_name, contact_info, gender FROM users"
                )
        
        users = []
        for row in result:
            user_data = {
                "username": row[0],
                "role": row[1],
                "name": row[2],
                "active": row[3],
                "first_name": row[4] if len(row) > 4 else None,
                "middle_name": row[5] if len(row) > 5 else None,
                "last_name": row[6] if len(row) > 6 else None,
                "contact_info": row[7] if len(row) > 7 else None,
                "gender": row[8] if len(row) > 8 else None,
                "strand": row[9] if len(row) > 9 else None,
                "payment_plan": row[10] if len(row) > 10 else None,
            }
            users.append(user_data)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    """Create a new user (For IT)."""
    client = get_db_client()
    try:
        # Check if exists
        check = client.sqlQuery(
            f"SELECT id FROM users WHERE username = '{user.username}'"
        )
        if check:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Students always get password "123" when creating
        password_to_use = "123" if user.role == "student" else user.password
        hashed_pw = get_password_hash(password_to_use)

        # Build display name from first_name + last_name if available
        display_name = user.name
        if user.first_name and user.last_name:
            display_name = f"{user.first_name} {user.last_name}"
        elif user.first_name:
            display_name = user.first_name
        elif user.last_name:
            display_name = user.last_name

        strand_val = (user.strand or "") if getattr(user, "strand", None) else ""
        payment_plan_val = (user.payment_plan or "") if getattr(user, "payment_plan", None) else ""
        if user.role == "student" and not payment_plan_val:
            payment_plan_val = "plan_a"
        query = f"""
            INSERT INTO users (username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender, strand, payment_plan)
            VALUES ('{user.username}', '{hashed_pw}', '{user.role}', '{display_name}', {user.active},
                    '{user.first_name or ""}', '{user.middle_name or ""}', '{user.last_name or ""}',
                    '{user.contact_info or ""}', '{user.gender or ""}', '{strand_val}', '{payment_plan_val}')
        """
        try:
            client.sqlExec(query)
        except Exception:
            query_fb = f"""
                INSERT INTO users (username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender)
                VALUES ('{user.username}', '{hashed_pw}', '{user.role}', '{display_name}', {user.active},
                        '{user.first_name or ""}', '{user.middle_name or ""}', '{user.last_name or ""}',
                        '{user.contact_info or ""}', '{user.gender or ""}')
            """
            client.sqlExec(query_fb)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{username}")
def update_user(username: str, user: UserUpdate):
    """Update user details or password (Admin/IT only)."""
    client = get_db_client()
    try:
        updates = []
        if user.role:
            updates.append(f"role = '{user.role}'")
        if user.name:
            updates.append(f"name = '{user.name}'")
        if user.active is not None:
            updates.append(f"active = {str(user.active).lower()}")
        if user.password:
            hashed_pw = get_password_hash(user.password)
            updates.append(f"hashed_password = '{hashed_pw}'")
        if user.first_name is not None:
            updates.append(f"first_name = '{user.first_name}'")
        if user.middle_name is not None:
            updates.append(f"middle_name = '{user.middle_name}'")
        if user.last_name is not None:
            updates.append(f"last_name = '{user.last_name}'")
        if user.contact_info is not None:
            updates.append(f"contact_info = '{user.contact_info}'")
        if user.gender is not None:
            updates.append(f"gender = '{user.gender}'")

        # Update display name if first/last name changed
        if user.first_name is not None or user.last_name is not None:
            # Get current values
            current = client.sqlQuery(f"SELECT first_name, last_name FROM users WHERE username = '{username}'")
            if current:
                fn = user.first_name if user.first_name is not None else (current[0][0] if current[0][0] else "")
                ln = user.last_name if user.last_name is not None else (current[0][1] if len(current[0]) > 1 and current[0][1] else "")
                if fn and ln:
                    updates.append(f"name = '{fn} {ln}'")
                elif fn:
                    updates.append(f"name = '{fn}'")
                elif ln:
                    updates.append(f"name = '{ln}'")

        if updates:
            set_clause = ", ".join(updates)
            client.sqlExec(f"UPDATE users SET {set_clause} WHERE username = '{username}'")

        # Update payment_plan in a separate UPDATE so missing column never fails the request
        if user.payment_plan is not None:
            if user.payment_plan not in ("", "plan_a", "plan_b", "plan_c"):
                raise HTTPException(status_code=400, detail="payment_plan must be plan_a, plan_b, or plan_c")
            try:
                client.sqlExec(f"UPDATE users SET payment_plan = '{user.payment_plan}' WHERE username = '{username}'")
            except Exception:
                pass  # column may not exist

        if not updates:
            return {"message": "No changes requested"}
        return {"message": "User updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProfileRequest(BaseModel):
    username: str


def _get_user_profile(username: str):
    """Internal helper to fetch user profile."""
    client = get_db_client()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    # Try to get strand and payment_plan if columns exist
    try:
        result = client.sqlQuery(
            f"SELECT username, role, name, first_name, middle_name, last_name, contact_info, gender, strand, payment_plan FROM users WHERE username = '{username}'"
        )
    except Exception:
        try:
            result = client.sqlQuery(
                f"SELECT username, role, name, first_name, middle_name, last_name, contact_info, gender, strand FROM users WHERE username = '{username}'"
            )
        except Exception:
            result = client.sqlQuery(
                f"SELECT username, role, name, first_name, middle_name, last_name, contact_info, gender FROM users WHERE username = '{username}'"
            )
    if not result or len(result) == 0:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    
    row = result[0]
    return {
        "username": row[0],
        "role": row[1],
        "name": row[2],
        "first_name": row[3] if len(row) > 3 and row[3] else None,
        "middle_name": row[4] if len(row) > 4 and row[4] else None,
        "last_name": row[5] if len(row) > 5 and row[5] else None,
        "contact_info": row[6] if len(row) > 6 and row[6] else None,
        "gender": row[7] if len(row) > 7 and row[7] else None,
        "strand": row[8] if len(row) > 8 and row[8] else None,
        "payment_plan": row[9] if len(row) > 9 and row[9] else None,
    }


@router.post("/profile")
def get_current_user_profile(req: ProfileRequest):
    """Get current user's profile."""
    try:
        return _get_user_profile(req.username)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Profile fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")


class ProfileUpdateRequest(BaseModel):
    username: str
    profile: UserProfileUpdate


@router.put("/profile")
def update_user_profile(req: ProfileUpdateRequest):
    """Update current user's own profile."""
    client = get_db_client()
    username = req.username
    profile = req.profile
    try:
        updates = []
        if profile.first_name is not None:
            updates.append(f"first_name = '{profile.first_name}'")
        if profile.middle_name is not None:
            updates.append(f"middle_name = '{profile.middle_name}'")
        if profile.last_name is not None:
            updates.append(f"last_name = '{profile.last_name}'")
        if profile.contact_info is not None:
            updates.append(f"contact_info = '{profile.contact_info}'")
        if profile.gender is not None:
            updates.append(f"gender = '{profile.gender}'")
        # Do NOT add payment_plan here — column may not exist; we update it separately below

        # Update display name
        if profile.first_name is not None or profile.last_name is not None:
            current = client.sqlQuery(f"SELECT first_name, last_name FROM users WHERE username = '{username}'")
            if current:
                fn = profile.first_name if profile.first_name is not None else (current[0][0] if current[0][0] else "")
                ln = profile.last_name if profile.last_name is not None else (current[0][1] if len(current[0]) > 1 and current[0][1] else "")
                if fn and ln:
                    updates.append(f"name = '{fn} {ln}'")
                elif fn:
                    updates.append(f"name = '{fn}'")
                elif ln:
                    updates.append(f"name = '{ln}'")

        if updates:
            set_clause = ", ".join(updates)
            client.sqlExec(f"UPDATE users SET {set_clause} WHERE username = '{username}'")

        # Update payment_plan in a separate UPDATE so missing column never fails the request
        payment_plan_set = False
        if profile.payment_plan is not None:
            if profile.payment_plan not in ("", "plan_a", "plan_b", "plan_c"):
                raise HTTPException(status_code=400, detail="payment_plan must be plan_a, plan_b, or plan_c")
            try:
                client.sqlExec(f"UPDATE users SET payment_plan = '{profile.payment_plan}' WHERE username = '{username}'")
                payment_plan_set = True
            except Exception:
                pass  # column may not exist; profile still updated

        if not updates and not payment_plan_set:
            return {"message": "No changes requested"}
        return {"message": "Profile updated successfully", "payment_plan_set": payment_plan_set}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PasswordChangeRequest(BaseModel):
    username: str
    current_password: str
    new_password: str


@router.put("/change-password")
def change_password(req: PasswordChangeRequest):
    """Change current user's password."""
    client = get_db_client()
    try:
        # Verify current password
        result = client.sqlQuery(
            f"SELECT hashed_password FROM users WHERE username = '{req.username}'"
        )
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        stored_hash = result[0][0]
        if not verify_password(req.current_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Update password
        new_hash = get_password_hash(req.new_password)
        client.sqlExec(f"UPDATE users SET hashed_password = '{new_hash}' WHERE username = '{req.username}'")

        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_header(h: str) -> str:
    """Normalize Excel column header for matching."""
    if not h:
        return ""
    return str(h).strip().lower().replace(" ", "_").replace("-", "_")


@router.post("/users/import-students")
async def import_students_excel(file: UploadFile = File(...)):
    """
    Import students from an Excel file. Expected columns (first row = headers):
    student_id (or username), last_name, first_name, middle_name, gender, strand, contact_information
    All imported users get role=student and password "123".
    """
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx)")

    try:
        import io
        from openpyxl import load_workbook

        contents = await file.read()
        wb = load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
        ws = wb.active
        if not ws:
            raise HTTPException(status_code=400, detail="Excel file has no sheet")

        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="Excel must have a header row and at least one data row")

        headers = [_normalize_header(str(c)) if c is not None else "" for c in rows[0]]
        col_map = {}
        for name in ("student_id", "username", "last_name", "first_name", "middle_name", "gender", "strand", "contact_information", "contact_info"):
            for i, h in enumerate(headers):
                if h == name or h == name.replace("_", ""):
                    col_map[name] = i
                    break
        if "contact_information" not in col_map and "contact_info" in col_map:
            col_map["contact_information"] = col_map["contact_info"]
        if "student_id" not in col_map and "username" in col_map:
            col_map["student_id"] = col_map["username"]
        if "student_id" not in col_map:
            raise HTTPException(status_code=400, detail="Excel must have a 'student_id' or 'username' column")

        def get_cell(row, key):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return ""
            v = row[idx]
            return "" if v is None else str(v).strip()

        def esc(s: str) -> str:
            return (s or "").replace("'", "''")

        client = get_db_client()
        hashed_pw = get_password_hash("123")
        created = 0
        skipped = []
        errors = []

        for row_idx, row in enumerate(rows[1:], start=2):
            if not any(v is not None and str(v).strip() for v in row):
                continue
            username = get_cell(row, "student_id") or get_cell(row, "username")
            if not username:
                errors.append(f"Row {row_idx}: missing student_id/username")
                continue
            last_name = get_cell(row, "last_name")
            first_name = get_cell(row, "first_name")
            middle_name = get_cell(row, "middle_name")
            gender = get_cell(row, "gender")
            strand_val = get_cell(row, "strand")
            contact = get_cell(row, "contact_information") or get_cell(row, "contact_info")
            display_name = f"{first_name} {last_name}".strip() or username

            try:
                check = client.sqlQuery(f"SELECT id FROM users WHERE username = '{esc(username)}'")
                if check:
                    skipped.append(username)
                    continue
                query = f"""
                    INSERT INTO users (username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender, strand, payment_plan)
                    VALUES ('{esc(username)}', '{hashed_pw}', 'student', '{esc(display_name)}', true,
                            '{esc(first_name)}', '{esc(middle_name)}', '{esc(last_name)}',
                            '{esc(contact)}', '{esc(gender)}', '{esc(strand_val)}', 'plan_a')
                """
                try:
                    client.sqlExec(query)
                    created += 1
                except Exception:
                    q2 = f"""
                        INSERT INTO users (username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender)
                        VALUES ('{esc(username)}', '{hashed_pw}', 'student', '{esc(display_name)}', true,
                                '{esc(first_name)}', '{esc(middle_name)}', '{esc(last_name)}', '{esc(contact)}', '{esc(gender)}')
                    """
                    client.sqlExec(q2)
                    created += 1
            except Exception as e:
                errors.append(f"Row {row_idx} ({username}): {str(e)}")

        return {
            "success": True,
            "created": created,
            "skipped_usernames": skipped,
            "errors": errors,
            "message": f"Created {created} student(s). Skipped {len(skipped)} existing. {len(errors)} error(s).",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.delete("/users/{username}")
def delete_user(username: str):
    """Delete a user (Admin only)."""
    client = get_db_client()
    try:
        # Check if user exists
        check = client.sqlQuery(f"SELECT id FROM users WHERE username = '{username}'")
        if not check:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user
        client.sqlExec(f"DELETE FROM users WHERE username = '{username}'")
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
