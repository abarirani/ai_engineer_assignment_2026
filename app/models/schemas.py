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
    CANCELLED = "cancelled"


class Recommendation(BaseModel):
    """A single visual recommendation for the image."""

    id: str = Field(..., description="Unique identifier for the recommendation")
    text: str = Field(..., description="Text description of the recommendation")
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1-5)")
    category: Optional[str] = Field(
        default=None, description="Category of recommendation (e.g., color, layout)"
    )


class BrandGuidelines(BaseModel):
    """Brand guidelines to respect during editing."""

    primary_colors: Optional[List[str]] = Field(
        default=None, description="Primary brand colors (hex codes)"
    )
    secondary_colors: Optional[List[str]] = Field(
        default=None, description="Secondary brand colors (hex codes)"
    )
    fonts: Optional[List[str]] = Field(
        default=None, description="Approved font families"
    )
    logo_url: Optional[str] = Field(
        default=None, description="URL or path to brand logo"
    )
    protected_regions: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Regions to protect from editing"
    )
    do_not_use_colors: Optional[List[str]] = Field(
        default=None, description="Colors that should not be used"
    )
    additional_rules: Optional[List[str]] = Field(
        default=None, description="Additional brand rules as text"
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
    evaluation_score: confloat(ge=0, le=1) = Field(
        ..., description="Quality evaluation score"
    )
    iterations: int = Field(..., ge=1, description="Number of iterations performed")
    audit_trail: List[Dict[str, Any]] = Field(
        ..., description="Detailed audit trail for this variant"
    )


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
    audit_trail: List[Dict[str, Any]] = Field(
        ..., description="Complete workflow audit trail"
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
