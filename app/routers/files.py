import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["Files"])

# Create a local directory to store images
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Receives a file, saves it with a unique ID, and returns the path.
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, detail="Only JPEG, PNG, or PDF files are allowed"
            )

        # Generate unique filename
        file_ext = file.filename.split(".")[-1]
        new_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, new_name)

        # Save the file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Return the path relative to the API URL
        # e.g., if API_URL is localhost:8000, this returns 'files/filename.png'
        # The frontend will append this to API_URL
        return {"path": f"files/{new_name}"}
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get("/{filename}")
async def get_file(filename: str):
    """
    Serve the file back to the browser.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")
