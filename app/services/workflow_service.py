"""Workflow service for executing the LangGraph agent workflow.

This module provides the business logic for running the multi-agent workflow,
separating it from the API layer for better testability and reusability.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.agents import compile_workflow
from app.models.schemas import JobStatusEnum

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for executing the LangGraph agent workflow.

    This service encapsulates all workflow execution logic, including:
    - Workflow compilation and initialization
    - Input state preparation
    - Workflow invocation
    - Result formatting

    Attributes:
        workflow_app: Compiled LangGraph workflow application.
    """

    def __init__(self) -> None:
        """Initialize the workflow service.

        Compiles the LangGraph workflow on initialization. If compilation
        fails, the service will be in a degraded state and workflow execution
        will raise RuntimeError.
        """
        self._workflow_app: Optional[Any] = None
        self._initialize_workflow()

    def _initialize_workflow(self) -> None:
        """Initialize and compile the LangGraph workflow.

        Raises:
            RuntimeError: If workflow compilation fails.
        """
        try:
            self._workflow_app = compile_workflow()
            logger.info("LangGraph workflow compiled successfully")
        except Exception as e:
            logger.error(f"Failed to compile LangGraph workflow: {e}")
            self._workflow_app = None

    @property
    def is_ready(self) -> bool:
        """Check if the workflow service is ready to execute workflows.

        Returns:
            True if the workflow is compiled and ready, False otherwise.
        """
        return self._workflow_app is not None

    async def run_workflow(
        self, job_id: str, job: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run the LangGraph agent workflow for a job.

        This method:
        1. Validates that the workflow is compiled
        2. Prepares the input state from the job data
        3. Invokes the workflow asynchronously
        4. Formats and returns the results

        Args:
            job_id: Unique job identifier.
            job: Job data containing request and image path.

        Returns:
            Workflow result dictionary containing:
            - job_id: The job identifier
            - status: Job completion status
            - input_image_url: URL of the input image
            - variants: List of generated variants with evaluation scores

        Raises:
            RuntimeError: If the workflow is not compiled.
        """
        if self._workflow_app is None:
            raise RuntimeError("LangGraph workflow not compiled")

        request = job["request"]
        image_path = job["image_path"]

        # Prepare input state for the workflow
        input_state = {
            "job_id": job_id,
            "input_image": image_path,
            "recommendations": [
                {
                    "id": rec.id,
                    "text": rec.text,
                    "priority": rec.priority,
                    "category": rec.category,
                }
                for rec in request.recommendations
            ],
            "brand_guidelines": (
                request.brand_guidelines.model_dump()
                if request.brand_guidelines
                else {}
            ),
            "tasks": [],
            "variants": [],
            "completed": False,
        }

        logger.info(f"Executing workflow for job {job_id}")

        # Run the workflow (using async invoke)
        final_state = await self._workflow_app.ainvoke(input_state)

        # Format the result
        variants = []
        for variant in final_state.get("variants", []):
            variants.append(
                {
                    "recommendation_id": variant["recommendation_id"],
                    "variant_url": variant.get("variant_data", ""),
                    "evaluation_score": variant["evaluation_score"],
                    "iterations": variant["iterations"],
                }
            )

        result = {
            "job_id": job_id,
            "status": JobStatusEnum.COMPLETED,
            "input_image_url": job.get("image_url"),
            "variants": variants,
        }

        logger.info(f"Workflow completed for job {job_id}")
        return result

    async def process_job(
        self, job_id: str, jobs: Dict[str, Dict]
    ) -> None:
        """Background task to process a job using the agent workflow.

        This method orchestrates the complete job processing lifecycle:
        1. Updates job status to PROCESSING
        2. Runs the agent workflow
        3. Updates job status to COMPLETED or FAILED
        4. Stores the result in the job record

        Args:
            job_id: Unique job identifier.
            jobs: The jobs dictionary for state management.
        """
        logger.info(f"Starting background processing for job: {job_id}")

        if job_id not in jobs:
            logger.error(f"Job not found: {job_id}")
            return

        job = jobs[job_id]
        job["status"] = JobStatusEnum.PROCESSING
        job["updated_at"] = datetime.utcnow()
        job["progress"] = 0
        job["message"] = "Processing started"

        try:
            logger.info(
                f"Processing job {job_id} with {len(job['request'].recommendations)} recommendations"
            )

            # Update progress
            job["progress"] = 20
            job["message"] = "Orchestrating tasks..."
            job["updated_at"] = datetime.utcnow()

            # Run the agent workflow
            job["progress"] = 50
            job["message"] = "Generating variants..."
            job["updated_at"] = datetime.utcnow()

            result = await self.run_workflow(job_id, job)

            # Complete processing
            job["progress"] = 100
            job["status"] = JobStatusEnum.COMPLETED
            job["completed_at"] = datetime.utcnow()
            job["message"] = "Processing completed successfully"
            job["result"] = result

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.exception(f"Error processing job {job_id}: {e}")
            job["status"] = JobStatusEnum.FAILED
            job["error"] = str(e)
            job["updated_at"] = datetime.utcnow()


# Singleton instance for use across the application
_workflow_service: Optional[WorkflowService] = None


def get_workflow_service() -> WorkflowService:
    """Get the singleton workflow service instance.

    Returns:
        The singleton WorkflowService instance.
    """
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service
