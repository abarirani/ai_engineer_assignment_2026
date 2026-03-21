"""API endpoint definitions."""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.models.schemas import (
    JobResult,
    JobStatus,
    JobStatusEnum,
    ProcessRequest,
    ProcessResponse,
)
from app.services import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job storage (replace with Redis/database in production)
jobs: Dict[str, Dict] = {}

# Initialize the workflow service
workflow_service = WorkflowService()


def generate_job_id() -> str:
    """Generate a unique job ID."""
    return str(uuid.uuid4())


async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file to disk and return path."""
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = Path(settings.upload_dir) / filename

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
    request: ProcessRequest,
    image: UploadFile = File(..., description="Image file to process"),
) -> ProcessResponse:
    """Process an image with visual recommendations.

    Args:
        request: Processing request with recommendations and brand guidelines
        image: Image file to process

    Returns:
        ProcessResponse with job ID for tracking

    Raises:
        HTTPException: For invalid file types or sizes
    """
    # Validate file type
    file_extension = Path(image.filename).suffix.lower()
    if file_extension not in settings.allowed_file_types:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Invalid file type: {file_extension}. "
                f"Allowed types: {', '.join(settings.allowed_file_types)}"
            },
        )

    # Generate job ID
    job_id = generate_job_id()

    # Save uploaded image
    image_path = await save_uploaded_file(image)
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
