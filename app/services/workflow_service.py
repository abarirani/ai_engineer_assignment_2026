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
from datetime import datetime
from typing import Dict, Optional

from app.agents.deep_agent_workflow import DeepAgentWorkflow
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
        _deep_agent_workflow: The DeepAgentWorkflow instance.
        _llm_strategy: The LLM strategy for model invocation.
    """

    def __init__(self) -> None:
        """Initialize the workflow service.

        Raises:
            RuntimeError: If workflow initialization fails.
        """
        try:
            self._deep_agent_workflow = DeepAgentWorkflow()
            logger.info("Deep Agent workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deep Agent workflow: {e}")
            self._deep_agent_workflow = None

    async def process_job(self, job_id: str, jobs: Dict[str, Dict]) -> None:
        """Background task to process a job using the Deep Agent workflow.

        This method orchestrates the complete job processing lifecycle:
        1. Initializes job-specific observability
        2. Updates job status to PROCESSING
        3. Runs the Deep Agent workflow
        4. Flushes traces to file
        5. Updates job status to COMPLETED or FAILED
        6. Stores the result in the job record

        Args:
            job_id: Unique job identifier.
            jobs: The jobs dictionary for state management.
        """
        logger.info(f"Starting background processing for job: {job_id}")

        if job_id not in jobs:
            logger.error(f"Job not found: {job_id}")
            return

        # Initialize job-specific observability
        init_observability_for_job(job_id, settings.storage.output_dir)
        logger.info(f"Observability initialized for job {job_id}")

        job = jobs[job_id]
        job["status"] = JobStatusEnum.PROCESSING
        job["updated_at"] = datetime.utcnow()
        job["progress"] = 0
        job["message"] = "Processing started"

        try:
            logger.info(
                f"Processing job {job_id} with {len(job['request'].recommendations)} recommendations"
            )

            result = await self._deep_agent_workflow.run_workflow(job_id, job)

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

        finally:
            # Flush traces to file and shutdown observability
            flush_job_traces()
            shutdown_job_observability()
            logger.info(f"Observability traces flushed for job {job_id}")


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
