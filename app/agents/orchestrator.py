"""Orchestrator agent for task decomposition and parallel execution.

The orchestrator breaks down recommendations into individual tasks and
dispatches them to worker nodes using LangGraph's Send API for parallel execution.
"""

from typing import Any, Dict, List

from langgraph.constants import Send

from .workflow import AgentState, TaskDefinition


def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """Orchestrator node that decomposes recommendations into tasks.

    This node:
    1. Reads the input recommendations from the state
    2. Creates task definitions for each recommendation

    Args:
        state: Current workflow state containing recommendations.

    Returns:
        State updates with task definitions.
    """
    recommendations = state.get("recommendations", [])
    brand_guidelines = state.get("brand_guidelines", {})
    input_image = state.get("input_image", "")

    # Create task definitions for each recommendation
    tasks: List[TaskDefinition] = []
    for rec in recommendations:
        task: TaskDefinition = {
            "recommendation_id": rec.get("id", ""),
            "recommendation_text": rec.get("text", ""),
            "priority": rec.get("priority", 1),
            "category": rec.get("category"),
            "image_data": input_image,
            "brand_guidelines": brand_guidelines,
        }
        tasks.append(task)

    return {"tasks": tasks}


def assign_workers(state: AgentState) -> List[Send]:
    """Assign workers to process each task in parallel.

    Uses LangGraph's Send API to dynamically create worker instances
    for each task. Each worker processes its task independently and
    writes results to the shared 'variants' key.

    Args:
        state: Current workflow state with task definitions.

    Returns:
        List of Send objects for parallel worker execution.
    """
    tasks = state.get("tasks", [])

    # Create a Send object for each task
    # Each worker will receive its own task in the input
    return [Send("worker", {"task": task}) for task in tasks]
