"""LangGraph workflow definition for the multi-agent system.

This module defines the state schemas and builds the StateGraph workflow
using the Orchestrator-Worker pattern for parallel task execution.
"""

from typing import Annotated, Any, Dict, List, Optional

import operator
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END


# =============================================================================
# State Schemas
# =============================================================================


class TaskDefinition(TypedDict):
    """Definition of a single task to be processed by a worker."""

    recommendation_id: str
    recommendation_text: str
    priority: int
    category: Optional[str]
    image_data: str
    brand_guidelines: Dict[str, Any]


class VariantOutput(TypedDict):
    """Output from a worker processing a task."""

    task_id: str
    recommendation_id: str
    variant_data: Optional[str]
    evaluation_score: float
    iterations: int
    status: str
    error: Optional[str]


class AgentState(TypedDict):
    """Main workflow state for the orchestrator graph.

    This state is shared across all nodes in the main workflow graph.
    """

    job_id: str
    input_image: str
    recommendations: List[Dict[str, Any]]
    brand_guidelines: Dict[str, Any]
    tasks: List[TaskDefinition]
    variants: Annotated[List[VariantOutput], operator.add]
    completed: bool


class WorkerState(TypedDict):
    """State for individual worker nodes.

    Each worker instance has its own state, but writes results to the
    shared 'variants' key in the main AgentState.
    """

    task: TaskDefinition
    variants: Annotated[List[VariantOutput], operator.add]


# =============================================================================
# Workflow Builder
# =============================================================================


def create_workflow() -> StateGraph:
    """Create and configure the multi-agent workflow.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Import node functions here to avoid circular imports
    from .orchestrator import orchestrator_node, assign_workers
    from .worker import worker_node
    from .synthesizer import synthesizer_node

    # Create the state graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("worker", worker_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define edges
    # Start -> Orchestrator
    workflow.add_edge(START, "orchestrator")

    # Orchestrator -> Workers (via conditional edges with Send API)
    workflow.add_conditional_edges(
        "orchestrator",
        assign_workers,
        # This will return Send objects for parallel execution
    )

    # Worker -> Synthesizer (all workers converge here)
    workflow.add_edge("worker", "synthesizer")

    # Synthesizer -> End
    workflow.add_edge("synthesizer", END)

    return workflow


def compile_workflow() -> Any:
    """Compile the workflow for execution.

    Returns:
        Compiled graph application.
    """
    workflow = create_workflow()
    return workflow.compile()
