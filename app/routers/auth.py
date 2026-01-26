from typing import List

from fastapi import APIRouter, HTTPException
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
        result = client.sqlQuery(
            "SELECT username, role, name, active, first_name, middle_name, last_name, contact_info, gender FROM users"
        )
        users = []
        for row in result:
            users.append(
                {
                    "username": row[0],
                    "role": row[1],
                    "name": row[2],
                    "active": row[3],
                    "first_name": row[4] if len(row) > 4 else None,
                    "middle_name": row[5] if len(row) > 5 else None,
                    "last_name": row[6] if len(row) > 6 else None,
                    "contact_info": row[7] if len(row) > 7 else None,
                    "gender": row[8] if len(row) > 8 else None,
                }
            )
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

        hashed_pw = get_password_hash(user.password)

        # Build display name from first_name + last_name if available
        display_name = user.name
        if user.first_name and user.last_name:
            display_name = f"{user.first_name} {user.last_name}"
        elif user.first_name:
            display_name = user.first_name
        elif user.last_name:
            display_name = user.last_name

        query = f"""
            INSERT INTO users (username, hashed_password, role, name, active, first_name, middle_name, last_name, contact_info, gender)
            VALUES ('{user.username}', '{hashed_pw}', '{user.role}', '{display_name}', {user.active},
                    '{user.first_name or ""}', '{user.middle_name or ""}', '{user.last_name or ""}',
                    '{user.contact_info or ""}', '{user.gender or ""}')
        """
        client.sqlExec(query)
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

        if not updates:
            return {"message": "No changes requested"}

        set_clause = ", ".join(updates)
        query = f"UPDATE users SET {set_clause} WHERE username = '{username}'"
        client.sqlExec(query)

        return {"message": "User updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProfileRequest(BaseModel):
    username: str


def _get_user_profile(username: str):
    """Internal helper to fetch user profile."""
    client = get_db_client()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
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

        if not updates:
            return {"message": "No changes requested"}

        set_clause = ", ".join(updates)
        query = f"UPDATE users SET {set_clause} WHERE username = '{username}'"
        client.sqlExec(query)

        return {"message": "Profile updated successfully"}
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
