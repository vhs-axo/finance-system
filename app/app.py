import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import auth, files, stats, transactions

# Initialize API
app = FastAPI(
    title="Financial Transparency API",
    description="Backend API for Senior High School Finance System using Immudb",
    version="1.0.0",
)

# 1. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Database Initialization
@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("static", exist_ok=True)  # Ensure static dir exists


# 3. Include Routers
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)
app.include_router(files.router, prefix="/files")

# 4. Mount Static Files
# This allows serving the frontend assets
app.mount("/static", StaticFiles(directory="static"), name="static")


# Root Endpoint -> Serve the Frontend
@app.get("/")
async def read_root():
    # Make sure static/index.html exists before running
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "status": "online",
        "system": "SHS Financial Transparency System",
        "docs": "/docs",  # Link to Swagger UI
    }
