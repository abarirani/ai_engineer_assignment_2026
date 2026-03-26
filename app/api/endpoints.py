"""API endpoint definitions."""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Request,
    BackgroundTasks,
    File,
    Form,
    UploadFile,
    status,
    HTTPException,
)
from fastapi.responses import JSONResponse, FileResponse

from app.config.settings import settings
from app.models.schemas import (
    JobResult,
    JobStatus,
    JobStatusEnum,
    ProcessRequest,
    ProcessResponse,
    VariantResult,
)
from app.utils import get_image_media_type

logger = logging.getLogger(__name__)

router = APIRouter()


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
    request: Request,
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Image file to process"),
    recommendations: str = Form(
        ..., description="JSON string of recommendations array"
    ),
    brand_guidelines: Optional[str] = Form(
        ..., description="JSON string of brand guidelines"
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

    try:
        brand_guidelines_data = json.loads(brand_guidelines)
    except json.JSONDecodeError as e:
        raise JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Invalid JSON in brand_guidelines: {str(e)}"},
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

    # Build ProcessRequest from parsed data
    process_request = ProcessRequest(
        recommendations=recommendations_data,
        brand_guidelines=brand_guidelines_data,
    )

    workflow_service = request.app.state.workflow_service

    # Create a new job and schedule background processing
    job_id = await workflow_service.create_job(
        image=image,
        process_request=process_request,
    )
    background_tasks.add_task(workflow_service.process_job, job_id)

    logger.info(
        f"Job {job_id} created with {len(process_request.recommendations)} recommendations"
    )

    return ProcessResponse(
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        message="Job queued for processing",
    )


@router.get(
    "/images/{job_id}/{image_type}/{filename}",
    summary="Get image",
    description="Retrieve an image by job ID, type, and filename.",
)
async def get_image(job_id: str, image_type: str, filename: str) -> FileResponse:
    """Serve an image by job ID, type, and filename.

    This endpoint serves both:
    - Uploaded input images (image_type='upload')
    - Generated variant images (image_type='variant')

    Args:
        job_id: The job ID associated with the image
        image_type: Type of image - 'upload' for input images, 'variant' for generated variants
        filename: The filename of the image

    Returns:
        FileResponse with the image content

    Raises:
        HTTPException: If image not found or invalid image_type
    """
    # Determine the directory based on image_type
    if image_type == "upload":
        base_dir = settings.storage.upload_dir
    elif image_type == "variant":
        base_dir = settings.storage.output_dir
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image_type: {image_type}. Must be 'upload' or 'variant'",
        )

    image_path = Path(base_dir) / job_id / filename

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {job_id}/{image_type}/{filename}",
        )

    return FileResponse(
        image_path,
        media_type=get_image_media_type(filename),
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatus,
    summary="Get job status",
    description="Check the current status of a processing job.",
)
async def get_job_status(request: Request, job_id: str) -> JobStatus:
    """Get the status of a processing job.

    Args:
        job_id: Unique job identifier

    Returns:
        JobStatus with current status and progress

    Raises:
        HTTPException: If job not found
    """
    workflow_service = request.app.state.workflow_service
    job = await workflow_service.get_job_status(job_id)
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
async def get_job_result(request: Request, job_id: str) -> JobResult:
    """Get the result of a completed job.

    Args:
        job_id: Unique job identifier

    Returns:
        JobResult with variants and audit trail

    Raises:
        HTTPException: If job not found or not completed
    """
    workflow_service = request.app.state.workflow_service
    job = await workflow_service.get_job_status(job_id)
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

    # Read report.json
    report_content = None
    report_path = Path(settings.storage.output_dir) / job_id / "report.json"
    if report_path.exists():
        report_content = json.loads(report_path.read_text())

    # Read messages.md
    messages_content = None
    messages_path = Path(settings.storage.output_dir) / job_id / "messages.md"
    if messages_path.exists():
        messages_content = messages_path.read_text()

    # Read traces.json
    trace_content = None
    trace_path = Path(settings.storage.output_dir) / job_id / "traces.json"
    if trace_path.exists():
        trace_content = json.loads(trace_path.read_text())

    # Parse variants from report if available
    variants = []
    if report_content and "variants" in report_content:
        for v in report_content["variants"]:
            # Convert local file path to API URL path
            local_path = v.get("path", "")
            if local_path:
                # Extract job_id and filename from the local path
                path_parts = Path(local_path).parts
                if len(path_parts) >= 2:
                    filename = path_parts[-1]
                    # Find the job_id in the path (it's the directory before the filename)
                    job_id_from_path = path_parts[-2]
                    # Use the new URL format with image_type (relative to API_BASE_URL)
                    variant_url = f"/images/{job_id_from_path}/variant/{filename}"
                else:
                    variant_url = local_path
            else:
                variant_url = ""

            variants.append(
                VariantResult(
                    recommendation_id=v.get("recommendation_id", ""),
                    variant_url=variant_url,
                    evaluation_score=v.get("evaluation_score", 0.0),
                    iterations=v.get("iterations", 1),
                )
            )

    return JobResult(
        job_id=job["job_id"],
        status=job["status"],
        input_image_url=job.get("image_url"),
        variants=variants,
        report_content=report_content,
        messages_content=messages_content,
        trace_content=trace_content,
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )
