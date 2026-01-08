from fastapi import APIRouter, HTTPException
from ..schemas import LoginRequest, LoginResponse
from ..database import get_db_client
from ..utils import verify_password

router = APIRouter(tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    client = get_db_client()
    try:
        # 1. Fetch user from DB
        # Note: We query by username and ensure the user is active
        query = f"SELECT username, hashed_password, role, name FROM users WHERE username = '{creds.username}' AND active = true"
        result = client.sqlQuery(query)
        
        if not result:
            return {"success": False, "message": "Invalid credentials"}
            
        # 2. Extract data from result
        user_row = result[0]
        stored_hash = user_row[1]
        role = user_row[2]
        name = user_row[3]
        
        # 3. Verify Password (using passlib/bcrypt)
        if verify_password(creds.password, stored_hash):
            return {
                "success": True, 
                "role": role, 
                "name": name, 
                "message": "Login successful"
            }
        else:
            return {"success": False, "message": "Invalid credentials"}
            
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
