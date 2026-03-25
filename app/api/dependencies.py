"""Dependency injection functions for FastAPI endpoints."""

from app.services.workflow_service import WorkflowService
from app.services import workflow_service


def init_dependencies(
    ws: WorkflowService
) -> None:
    """Initialize singleton dependencies (called from main.py lifespan).

    Args:
        db: Database instance to use across the application
        workflow_service: Workflow service instance to use across the application
        semaphore_manager: Semaphore manager instance to use across the application
    """
    workflow_service._workflow_service_instance = ws
