import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["Files"])

# Ensure upload directory exists
UPLOAD_DIR = "uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/files/upload", response_model=dict)
async def upload_proof(file: UploadFile = File(...)):
    """
    Upload a receipt image and return the file path.
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
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Return the relative path for storage in DB
        return {"filename": unique_name, "path": file_path}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/files/uploads/receipts/{filename}")
async def get_proof(filename: str):
    """
    Serve the uploaded file.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
