from pydantic import BaseModel


# --- AUTH & USER SCHEMAS ---
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    role: str | None = None
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    message: str


class UserBase(BaseModel):
    username: str
    role: str
    name: str
    active: bool = True
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    contact_info: str | None = None
    gender: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    role: str | None = None
    name: str | None = None
    active: bool | None = None
    password: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    contact_info: str | None = None
    gender: str | None = None


class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    contact_info: str | None = None
    gender: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


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
    tx_hash: str | None = None


class ApprovalRequest(BaseModel):
    admin_username: str
    action: str  # 'Approve' or 'Reject'


class AdminActionRequest(BaseModel):
    admin_username: str


class TransactionUpdateAdmin(BaseModel):
    admin_username: str
    txn_type: str | None = None
    strand: str | None = None
    category: str | None = None
    description: str | None = None
    amount: float | None = None
    status: str | None = None
    student_id: str | None = None
    proof_reference: str | None = None


# --- STATS SCHEMAS ---
class DashboardStats(BaseModel):
    total_tuition: float
    total_misc: float
    total_org: float
    total_expenses: float
    pending_count: int
    collections_by_category: dict
    disbursements_by_category: dict