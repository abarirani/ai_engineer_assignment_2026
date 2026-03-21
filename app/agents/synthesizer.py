"""Synthesizer agent for aggregating worker results.

The synthesizer collects all variant outputs from parallel workers
and assembles the final result.
"""

from typing import Any, Dict, List

from .workflow import AgentState, VariantOutput


def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizer node that aggregates all worker results.

    This node marks the workflow as completed after all workers finish.

    Args:
        state: Current workflow state with all worker outputs.

    Returns:
        State updates marking completion.
    """
    return {"completed": True}


def assemble_final_result(state: AgentState) -> Dict[str, Any]:
    """Assemble the final result from the workflow state.

    This function can be called after the workflow completes to
    format the results for the API response.

    Args:
        state: Final workflow state.

    Returns:
        Formatted result dictionary.
    """
    job_id = state.get("job_id", "unknown")
    variants: List[VariantOutput] = state.get("variants", [])

    # Format variants for response
    formatted_variants = []
    for variant in variants:
        formatted_variants.append(
            {
                "recommendation_id": variant["recommendation_id"],
                "variant_data": variant["variant_data"],
                "evaluation_score": variant["evaluation_score"],
                "iterations": variant["iterations"],
                "status": variant["status"],
                "error": variant["error"],
            }
        )

    return {
        "job_id": job_id,
        "status": "completed" if state.get("completed") else "failed",
        "variants": formatted_variants,
    }
