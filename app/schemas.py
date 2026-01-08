from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    name: Optional[str] = None
    message: str

class TransactionCreate(BaseModel):
    recorded_by: str
    txn_type: str
    strand: str
    category: str
    description: str
    amount: float

class TransactionResponse(BaseModel):
    id: int
    created_at: str
    recorded_by: str
    txn_type: str
    strand: str
    category: str
    description: str
    amount: float
    status: str

class DashboardStats(BaseModel):
    total_tuition: float
    total_misc: float
    total_org: float
    total_expenses: float
