import uuid
import os
import shutil
from pathlib import Path
from fastapi import UploadFile


def generate_unique_id() -> str:
    """Generate a unique job ID."""
    return str(uuid.uuid4())


def save_job_inputs(job_id: str, file: UploadFile, upload_dir: str) -> str:
    """Save uploaded file and associated metadata to disk.

    Args:
        job_id: Unique job identifier
        file: Uploaded file to save

    Returns:
        Path to the saved image file
    """
    upload_dir = Path(upload_dir) / job_id
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{file.filename}"
    file_path = upload_dir / filename

    # Ensure upload directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Use synchronous file operations
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_path)
