"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, confloat


class JobStatusEnum(str, Enum):
    """Job processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationType(str, Enum):
    """Types of visual recommendations."""

    CONTRAST_SALIENCE = "contrast_salience"
    COMPOSITION = "composition"
    COLOUR_MOOD = "colour_mood"
    COPY_MESSAGING = "copy_messaging"


class Recommendation(BaseModel):
    """A single visual recommendation for the image."""

    id: str = Field(..., description="Unique identifier for the recommendation")
    title: str = Field(..., description="Title/summary of the recommendation")
    description: str = Field(
        ..., description="Detailed description of the recommendation"
    )
    type: RecommendationType = Field(..., description="Type of recommendation")


class BrandGuidelines(BaseModel):
    """Brand guidelines to respect during editing."""

    protected_regions: Optional[List[str]] = Field(
        default=None,
        description="List of regions or elements that should not be modified",
    )
    typography: Optional[str] = Field(
        default=None, description="Typography guidelines for text elements"
    )
    aspect_ratio: Optional[str] = Field(
        default=None, description="Required aspect ratio to maintain"
    )
    brand_elements: Optional[str] = Field(
        default=None,
        description="Guidelines for brand elements visibility and placement",
    )


class ProcessRequest(BaseModel):
    """Request schema for image processing."""

    recommendations: List[Recommendation] = Field(
        ..., min_length=1, description="List of recommendations to apply"
    )
    brand_guidelines: Optional[BrandGuidelines] = Field(
        default=None, description="Brand guidelines to follow"
    )
    image_id: Optional[str] = Field(
        default=None, description="ID of uploaded image (if pre-uploaded)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class JobStatus(BaseModel):
    """Job status response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(default=None, description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class VariantResult(BaseModel):
    """Result for a single generated variant."""

    recommendation_id: str = Field(..., description="Original recommendation ID")
    variant_url: str = Field(..., description="URL to the generated variant")
    evaluation_score: confloat(ge=0, le=10) = Field(
        ..., description="Quality evaluation score (0-10 scale)"
    )
    iterations: int = Field(..., ge=1, description="Number of iterations performed")


class JobResult(BaseModel):
    """Complete job result with all variants."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(..., description="Final job status")
    input_image_url: Optional[str] = Field(
        default=None, description="URL to the input image"
    )
    variants: List[VariantResult] = Field(
        default=[], description="List of generated variants"
    )
    report_content: Optional[Dict[str, Any]] = Field(
        default=None, description="Content of report.json"
    )
    messages_content: Optional[str] = Field(
        default=None, description="Content of messages.md"
    )
    trace_content: Optional[Dict[str, Any]] = Field(
        default=None, description="Content of trace.json"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(
        default=None, description="Job completion timestamp"
    )


class ProcessResponse(BaseModel):
    """Response for process request."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(
        default=JobStatusEnum.PENDING, description="Job status"
    )
    message: str = Field(..., description="Response message")
