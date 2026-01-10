from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import auth, files, stats, transactions

# Initialize API
app = FastAPI(
    title="Financial Transparency API",
    description="Backend API for Senior High School Finance System using Immudb",
    version="1.0.0",
)

# 1. CORS Configuration
# Allows the Streamlit frontend (usually on port 8501) to talk to this API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Database Initialization on Startup
@app.on_event("startup")
def on_startup():
    init_db()


# 3. Include Routers
# These map the endpoints from the routers folder to the main app
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)
app.include_router(files.router)


# Root check
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "SHS Financial Transparency System",
        "docs": "/docs",  # Link to Swagger UI
    }
