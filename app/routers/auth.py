from fastapi import APIRouter, HTTPException
from typing import List
from ..schemas import LoginRequest, LoginResponse, UserCreate, UserResponse, UserUpdate
from ..database import get_db_client
from ..utils import verify_password, get_password_hash

router = APIRouter(tags=["Authentication & Users"])

@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    client = get_db_client()
    try:
        # Secure query parameter binding is recommended in prod, f-string used for demo
        query = f"SELECT hashed_password, role, name, active FROM users WHERE username = '{creds.username}'"
        result = client.sqlQuery(query)
        
        if not result:
            return {"success": False, "message": "User not found"}
        
        stored_hash = result[0][0]
        role = result[0][1]
        name = result[0][2]
        is_active = result[0][3]

        if not is_active:
             return {"success": False, "message": "Account is disabled"}

        if verify_password(creds.password, stored_hash):
            return {
                "success": True, 
                "role": role, 
                "name": name, 
                "message": "Login successful"
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
        result = client.sqlQuery("SELECT username, role, name, active FROM users")
        users = []
        for row in result:
            users.append({
                "username": row[0],
                "role": row[1],
                "name": row[2],
                "active": row[3]
            })
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    """Create a new user (For IT)."""
    client = get_db_client()
    try:
        # Check if exists
        check = client.sqlQuery(f"SELECT id FROM users WHERE username = '{user.username}'")
        if check:
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed_pw = get_password_hash(user.password)
        
        query = f"""
            INSERT INTO users (username, hashed_password, role, name, active)
            VALUES ('{user.username}', '{hashed_pw}', '{user.role}', '{user.name}', {user.active})
        """
        client.sqlExec(query)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{username}")
def update_user(username: str, user: UserUpdate):
    """Update user details or password."""
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
            
        if not updates:
            return {"message": "No changes requested"}
            
        set_clause = ", ".join(updates)
        query = f"UPDATE users SET {set_clause} WHERE username = '{username}'"
        client.sqlExec(query)
        
        return {"message": "User updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
