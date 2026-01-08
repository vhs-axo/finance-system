from fastapi import APIRouter
from ..schemas import LoginRequest, LoginResponse
from ..database import get_db_client
from ..utils import verify_password

router = APIRouter(tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    client = get_db_client()
    try:
        # 1. Query the user from the database
        # Note: We use f-string for simplicity in this demo, but use param binding in prod to prevent SQL injection
        query = f"SELECT hashed_password, role, name, active FROM users WHERE username = '{creds.username}'"
        result = client.sqlQuery(query)
        
        if not result:
            return {"success": False, "message": "User not found"}
        
        # 2. Extract data (Immudb returns a list of tuples)
        stored_hash = result[0][0]
        role = result[0][1]
        name = result[0][2]
        is_active = result[0][3]

        if not is_active:
             return {"success": False, "message": "Account is disabled"}

        # 3. Verify Password using Scrypt
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
        return {"success": False, "message": "System error during login"}
