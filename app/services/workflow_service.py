"""Workflow service for executing the Deep Agents workflow.

This module provides the business logic for running the simplified Deep Agents
workflow, separating it from the API layer for better testability and reusability.

The Deep Agents approach simplifies the workflow by:
- Using a single agent instead of orchestrator + worker + synthesizer nodes
- Leveraging built-in task planning via write_todos tool
- Using built-in subagent spawning for parallel variant generation
- Managing context via filesystem backend instead of TypedDict state schemas
"""

import logging
from typing import Dict, Any
from pathlib import Path

from fastapi import UploadFile
from app.agents.deep_agent_workflow import DeepAgentWorkflow
from app.services.semaphore_manager import SemaphoreManager
from app.models.database import JobDatabase
from app.models.schemas import JobStatusEnum
from app.observability import (
    init_observability_for_job,
    flush_job_traces,
    shutdown_job_observability,
)
from app.models.schemas import ProcessRequest
from app.config.settings import settings
from app.utils import generate_unique_id, save_job_inputs


logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for executing the Deep Agents workflow.

    This service encapsulates all workflow execution logic, including:
    - Deep Agent initialization with LLM strategy
    - Job processing and lifecycle management
    - Result formatting

    Attributes:
        _db: The JobDatabase instance for persistent job storage.
        _deep_agent_workflow: The DeepAgentWorkflow instance.
    """

    def __init__(self) -> None:
        """Initialize the workflow service.

        Raises:
            RuntimeError: If workflow initialization fails.
        """
        self._semaphore_manager = SemaphoreManager(settings.processing.max_concurrent_jobs)

        self._db = JobDatabase(settings.database.path)

        # Recover any stale processing jobs from unexpected shutdowns
        recovered_count = self._db.recover_stale_processing_jobs()
        if recovered_count > 0:
            logger.warning(
                f"Recovered {recovered_count} stale processing job(s) marked as failed"
            )
        else:
            logger.info("No stale processing jobs found")

        try:
            self._deep_agent_workflow = DeepAgentWorkflow()
            logger.info("Deep Agent workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deep Agent workflow: {e}")
            self._deep_agent_workflow = None

    async def create_job(
        self,
        image: UploadFile,
        recommendations_data,
        brand_guidelines_data,
        request: ProcessRequest,
    ) -> str:
        """Create a new job.

        Args:
            image (UploadFile): _description_
            recommendations_data (_type_): _description_
            brand_guidelines_data (_type_): _description_
            request (ProcessRequest): _description_

        Returns:
            str: _description_
        """
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
        self._db.create_job(job_id, request_dict, image_path, image_url)

        return job_id

    async def process_job(self, job_id: str) -> None:
        """Background task to process a job using the Deep Agent workflow.

        This method orchestrates the complete job processing lifecycle:
        1. Acquires semaphore slot (limits concurrent jobs)
        2. Fetches job from database
        3. Initializes job-specific observability
        4. Updates job status to PROCESSING
        5. Runs the Deep Agent workflow
        6. Flushes traces to file
        7. Updates job status to COMPLETED or FAILED
        8. Releases semaphore slot

        Args:
            job_id: Unique job identifier.
        """
        logger.info(f"Starting background processing for job: {job_id}")

        # Acquire semaphore slot (blocks if max concurrent jobs reached)
        await self._semaphore_manager.acquire(job_id)

        try:
            # Fetch job from database
            job = self._db.get_job(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return

            # Initialize job-specific observability
            init_observability_for_job(job_id, settings.storage.output_dir)
            logger.info(f"Observability initialized for job {job_id}")

            # Update status to PROCESSING via database
            self._db.update_job_status(
                job_id,
                JobStatusEnum.PROCESSING,
                progress=0,
                message="Processing started",
            )

            try:
                logger.info(
                    f"Processing job {job_id} with {len(job['request']['recommendations'])} recommendations"
                )

                status = await self._deep_agent_workflow.run_workflow(job_id, job)

                if status == "success":
                    self._db.complete_job(job_id)
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    self._db.update_job_status(
                        job_id,
                        JobStatusEnum.FAILED,
                        progress=100,
                        message="Report validation failed",
                    )
                    logger.warning(f"Job {job_id} failed report validation")

            except Exception as e:
                logger.exception(f"Error processing job {job_id}: {e}")
                self._db.fail_job(job_id, str(e))

            finally:
                # Flush traces to file and shutdown observability
                flush_job_traces(job_id)
                shutdown_job_observability(job_id)
                logger.info(f"Observability traces flushed for job {job_id}")

        finally:
            # Release semaphore slot
            await self._semaphore_manager.release(job_id)

    async def get_job_status(self, job_id: str) -> [Dict[str, Any]]:
        """Get job status."""
        return self._db.get_job(job_id)


_workflow_service_instance: WorkflowService = None


def get_workflow_service() -> WorkflowService:
    """Workflow service dependency - returns singleton instance.

    Returns:
        WorkflowService instance

    Raises:
        RuntimeError: If workflow service has not been initialized
    """
    global _workflow_service_instance
    if _workflow_service_instance is None:
        raise RuntimeError("Workflow service not initialized")
    return _workflow_service_instance
