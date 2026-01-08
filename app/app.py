from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, transactions, stats
from .database import init_db

# Initialize API
app = FastAPI(
    title="Financial Transparency API",
    description="Backend API for Senior High School Finance System using Immudb",
    version="1.0.0"
)

# 1. CORS Configuration (Allows frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Database Initialization on Startup
@app.on_event("startup")
def on_startup():
    init_db()

# 3. Include Routers (Modular Endpoints)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)

# Root check
@app.get("/")
def read_root():
    return {"status": "online", "system": "Financial Transparency API"}
