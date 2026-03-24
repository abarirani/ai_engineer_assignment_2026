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
from typing import Optional

from app.agents.deep_agent_workflow import DeepAgentWorkflow
from app.models.database import JobDatabase
from app.models.schemas import JobStatusEnum
from app.observability import (
    init_observability_for_job,
    flush_job_traces,
    shutdown_job_observability,
)
from app.config.settings import settings

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

    def __init__(self, db: JobDatabase) -> None:
        """Initialize the workflow service.

        Args:
            db: JobDatabase instance for persistent job storage.

        Raises:
            RuntimeError: If workflow initialization fails.
        """
        self._db = db
        try:
            self._deep_agent_workflow = DeepAgentWorkflow()
            logger.info("Deep Agent workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deep Agent workflow: {e}")
            self._deep_agent_workflow = None

    async def process_job(self, job_id: str) -> None:
        """Background task to process a job using the Deep Agent workflow.

        This method orchestrates the complete job processing lifecycle:
        1. Fetches job from database
        2. Initializes job-specific observability
        3. Updates job status to PROCESSING
        4. Runs the Deep Agent workflow
        5. Flushes traces to file
        6. Updates job status to COMPLETED or FAILED

        Args:
            job_id: Unique job identifier.
        """
        logger.info(f"Starting background processing for job: {job_id}")

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


# Singleton instance for use across the application
_workflow_service: Optional[WorkflowService] = None


def get_workflow_service(db: Optional[JobDatabase] = None) -> WorkflowService:
    """Get the singleton workflow service instance.

    Args:
        db: Optional JobDatabase instance. If provided, creates a new instance.

    Returns:
        The singleton WorkflowService instance.
    """
    global _workflow_service
    if _workflow_service is None:
        if db is None:
            raise ValueError(
                "JobDatabase instance must be provided to get_workflow_service()"
            )
        _workflow_service = WorkflowService(db)
    return _workflow_service
