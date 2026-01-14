"""
File storage utilities for insurance card uploads
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

# Optional Pillow for image validation
try:
    from PIL import Image
    import io
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("WARNING: Pillow not installed. Image validation will be limited. Install with: pip install pillow")

# Storage configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def ensure_upload_dir():
    """Ensure upload directory exists"""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_image_file(file: UploadFile) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded image file
    Returns (is_valid, error_message)
    """
    # Check file extension
    if not file.filename:
        return False, "No filename provided"
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid MIME type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
    
    return True, None


async def save_insurance_card(
    file: UploadFile,
    student_uuid: str,
    side: str  # "front" or "back"
) -> str:
    """
    Save insurance card image and return filename
    
    Args:
        file: Uploaded file
        student_uuid: Student UUID for unique naming
        side: "front" or "back"
    
    Returns:
        Filename (not full path) for database storage
    """
    # Validate file
    is_valid, error = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Validate it's actually an image (if Pillow is available)
    if PILLOW_AVAILABLE:
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()  # Verify it's a valid image
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file: {str(e)}"
            )
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    unique_filename = f"{student_uuid}_{side}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    # Ensure upload directory exists
    upload_dir = ensure_upload_dir()
    file_path = Path(upload_dir) / unique_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return filename only (we'll use the filename to serve files)
    # This makes it easier to construct URLs and serve files
    return unique_filename


async def delete_insurance_card(file_path: str):
    """Delete insurance card file"""
    try:
        full_path = Path(file_path)
        if full_path.exists():
            full_path.unlink()
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

