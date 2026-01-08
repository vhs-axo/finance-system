from fastapi import APIRouter
from ..schemas import LoginRequest, LoginResponse
from ..core import USERS

router = APIRouter(tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(creds: LoginRequest):
    user = USERS.get(creds.username)
    if user and user['password'] == creds.password:
        return {
            "success": True, 
            "role": user['role'], 
            "name": user['name'], 
            "message": "Login successful"
        }
    return {"success": False, "message": "Invalid credentials"}
