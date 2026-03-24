"""API endpoint definitions."""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.models.schemas import (
    JobResult,
    JobStatus,
    JobStatusEnum,
    ProcessRequest,
    ProcessResponse,
)
from app.services.workflow_service import get_workflow_service
from app.utils import generate_unique_id

logger = logging.getLogger(__name__)

router = APIRouter()

# TODO: In-memory job storage (replace with sqlite in production)
jobs: Dict[str, Dict] = {}

# Get the workflow service (initialized in main.py)
workflow_service = get_workflow_service()


async def save_job_inputs(job_id: str, file: UploadFile) -> str:
    """Save uploaded file to disk and return path."""
    upload_dir = Path(settings.storage.upload_dir) / job_id
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{file.filename}"
    file_path = upload_dir / filename

    # Ensure upload directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_path)


@router.post(
    "/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process image with recommendations",
    description="Submit an image with visual recommendations for processing. "
    "The system will generate variants based on the recommendations while "
    "respecting brand guidelines.",
)
async def process_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Image file to process"),
    recommendations: str = Form(..., description="JSON string of recommendations array"),
    brand_guidelines: Optional[str] = Form(None, description="JSON string of brand guidelines"),
) -> ProcessResponse:
    """Process an image with visual recommendations.

    Args:
        image: Image file to process
        recommendations: JSON string containing array of recommendations
        brand_guidelines: Optional JSON string containing brand guidelines

    Returns:
        ProcessResponse with job ID for tracking

    Raises:
        HTTPException: For invalid file types or sizes
    """
    # Parse JSON form fields
    try:
        recommendations_data = json.loads(recommendations)
    except json.JSONDecodeError as e:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Invalid JSON in recommendations: {str(e)}"},
        )

    brand_guidelines_data = None
    if brand_guidelines:
        try:
            brand_guidelines_data = json.loads(brand_guidelines)
        except json.JSONDecodeError as e:
            raise JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Invalid JSON in brand_guidelines: {str(e)}"},
            )

    # Build ProcessRequest from parsed data
    request = ProcessRequest(
        recommendations=recommendations_data,
        brand_guidelines=brand_guidelines_data,
    )

    # Validate file type
    file_extension = Path(image.filename).suffix.lower()
    if file_extension not in settings.processing.allowed_file_types:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Invalid file type: {file_extension}. "
                f"Allowed types: {', '.join(settings.processing.allowed_file_types)}"
            },
        )

    # Generate job ID
    job_id = generate_unique_id()

    # Save uploaded image
    image_path = await save_job_inputs(job_id, image)
    image_url = f"/api/v1/images/{Path(image_path).name}"

    # Create job record
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatusEnum.PENDING,
        "request": request,
        "image_path": image_path,
        "image_url": image_url,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "progress": 0,
        "message": "Job queued for processing",
    }

    # Schedule background processing
    background_tasks.add_task(workflow_service.process_job, job_id, jobs)

    logger.info(
        f"Job {job_id} created with {len(request.recommendations)} recommendations"
    )

    return ProcessResponse(
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        message="Job queued for processing",
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatus,
    summary="Get job status",
    description="Check the current status of a processing job.",
)
async def get_job_status(job_id: str) -> JobStatus:
    """Get the status of a processing job.

    Args:
        job_id: Unique job identifier

    Returns:
        JobStatus with current status and progress

    Raises:
        HTTPException: If job not found
    """
    if job_id not in jobs:
        raise JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Job not found: {job_id}"},
        )

    job = jobs[job_id]

    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        progress=job.get("progress", 0),
        message=job.get("message"),
        error=job.get("error"),
    )


@router.get(
    "/result/{job_id}",
    response_model=JobResult,
    summary="Get job result",
    description="Retrieve the complete result of a processing job including "
    "generated variants and audit trail.",
)
async def get_job_result(job_id: str) -> JobResult:
    """Get the result of a completed job.

    Args:
        job_id: Unique job identifier

    Returns:
        JobResult with variants and audit trail

    Raises:
        HTTPException: If job not found or not completed
    """
    if job_id not in jobs:
        raise JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Job not found: {job_id}"},
        )

    job = jobs[job_id]

    if job["status"] != JobStatusEnum.COMPLETED:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Job not completed. Current status: {job['status'].value}"
            },
        )

    result = job.get("result")
    if not result:
        raise JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Job completed but no result available"},
        )

    return JobResult(**result)
