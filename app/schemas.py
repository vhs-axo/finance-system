from pydantic import BaseModel

# --- AUTH & USER SCHEMAS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    role: str | None = None
    name: str | None = None
    message: str

class UserBase(BaseModel):
    username: str
    role: str
    name: str
    active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    role: str | None = None
    name: str | None = None
    active: bool | None = None
    password: str | None = None

class UserResponse(UserBase):
    pass

# --- STUDENT SCHEMAS ---
class StudentCreate(BaseModel):
    student_id: str
    name: str
    strand: str

class StudentResponse(BaseModel):
    id: int
    student_id: str
    name: str
    strand: str
    status: str

# --- TRANSACTION SCHEMAS ---
class TransactionCreate(BaseModel):
    recorded_by: str
    txn_type: str
    strand: str
    category: str
    description: str
    amount: float
    student_id: str | None = None
    proof_reference: str | None = None  # Added for Evidence/Receipt Ref

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
    student_id: str | None = None
    approved_by: str | None = None
    approval_date: str | None = None
    proof_reference: str | None = None

class ApprovalRequest(BaseModel):
    admin_username: str
    action: str  # 'Approve' or 'Reject'

# --- STATS SCHEMAS ---
class DashboardStats(BaseModel):
    total_tuition: float
    total_misc: float
    total_org: float
    total_expenses: float
    pending_count: int
