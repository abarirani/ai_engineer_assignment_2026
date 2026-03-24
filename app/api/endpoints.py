"""API endpoint definitions."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.models.database import JobDatabase
from app.models.schemas import (
    JobResult,
    JobStatus,
    JobStatusEnum,
    ProcessRequest,
    ProcessResponse,
)
from app.utils import generate_unique_id, save_job_inputs

if TYPE_CHECKING:
    from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter()

# Database instance (initialized in main.py)
db: Optional[JobDatabase] = None

# Workflow service instance (initialized in main.py)
workflow_service: Optional["WorkflowService"] = None


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
    recommendations: str = Form(
        ..., description="JSON string of recommendations array"
    ),
    brand_guidelines: Optional[str] = Form(
        None, description="JSON string of brand guidelines"
    ),
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
    image_path = save_job_inputs(
        job_id,
        image,
        settings.storage.upload_dir,
        recommendations_data,
        brand_guidelines_data,
    )
    image_url = f"/api/v1/images/{Path(image_path).name}"

    # Create job in database
    request_dict = {
        "recommendations": [r.dict() for r in request.recommendations],
        "brand_guidelines": (
            request.brand_guidelines.dict() if request.brand_guidelines else None
        ),
    }
    db.create_job(job_id, request_dict, image_path, image_url)

    # Schedule background processing
    background_tasks.add_task(workflow_service.process_job, job_id)

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
    job = db.get_job(job_id)
    if not job:
        raise JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Job not found: {job_id}"},
        )

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
    job = db.get_job(job_id)
    if not job:
        raise JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Job not found: {job_id}"},
        )

    if job["status"] != JobStatusEnum.COMPLETED:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Job not completed. Current status: {job['status'].value}"
            },
        )

    # Job completed - return success response
    return JobResult(
        job_id=job["job_id"],
        status=job["status"],
        input_image_url=job.get("image_url"),
        variants=[],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )
