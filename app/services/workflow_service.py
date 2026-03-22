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
from typing import Any, Dict, Optional

from app.agents.deep_agent_workflow import DeepAgentWorkflow
from app.models.schemas import JobStatusEnum
from app.services.llm.strategy import LLMStrategy

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

    def __init__(self, llm_strategy: LLMStrategy) -> None:
        """Initialize the workflow service.

        Args:
            llm_strategy: The LLM strategy for model invocation.

        Raises:
            RuntimeError: If workflow initialization fails.
        """
        self._llm_strategy = llm_strategy
        self._deep_agent_workflow: Optional[DeepAgentWorkflow] = None
        self._initialize_workflow()

    def _initialize_workflow(self) -> None:
        """Initialize the Deep Agent workflow.

        Raises:
            RuntimeError: If workflow initialization fails.
        """
        try:
            self._deep_agent_workflow = DeepAgentWorkflow(self._llm_strategy)
            logger.info("Deep Agent workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deep Agent workflow: {e}")
            self._deep_agent_workflow = None

    @property
    def is_ready(self) -> bool:
        """Check if the workflow service is ready to execute workflows.

        Returns:
            True if the workflow is initialized and ready, False otherwise.
        """
        return self._deep_agent_workflow is not None

    async def run_workflow(self, job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Deep Agent workflow for a job.

        This method:
        1. Validates that the workflow is initialized
        2. Invokes the Deep Agent asynchronously
        3. Formats and returns the results

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
            RuntimeError: If the workflow is not initialized.
        """
        if self._deep_agent_workflow is None:
            raise RuntimeError("Deep Agent workflow not initialized")

        logger.info(f"Executing Deep Agent workflow for job {job_id}")

        # Run the workflow using Deep Agent
        result = await self._deep_agent_workflow.process_job(job_id, job)

        logger.info(f"Deep Agent workflow completed for job {job_id}")
        return result

    async def process_job(self, job_id: str, jobs: Dict[str, Dict]) -> None:
        """Background task to process a job using the Deep Agent workflow.

        This method orchestrates the complete job processing lifecycle:
        1. Updates job status to PROCESSING
        2. Runs the Deep Agent workflow
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
            job["message"] = "Planning tasks with Deep Agent..."
            job["updated_at"] = datetime.utcnow()

            # Run the Deep Agent workflow
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


def get_workflow_service(llm_strategy: Optional[LLMStrategy] = None) -> WorkflowService:
    """Get the singleton workflow service instance.

    Args:
        llm_strategy: Optional LLM strategy. If not provided, the existing
            singleton instance is returned.

    Returns:
        The singleton WorkflowService instance.
    """
    global _workflow_service
    if _workflow_service is None and llm_strategy is not None:
        _workflow_service = WorkflowService(llm_strategy)
    return _workflow_service
