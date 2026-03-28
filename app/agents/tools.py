import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple
from pathlib import Path
import re

from PIL import Image
from langchain_core.runnables import RunnableConfig
from langchain.tools import ToolRuntime

from app.config.settings import settings
from app.services.memory_service import memory_services
from app.services.image_editing.editor import ImageEditor
from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy_factory import ImageEditingStrategyFactory
from app.services.evaluation.strategy_factory import EvaluationStrategyFactory

logger = logging.getLogger(__name__)


def execute_edit(prompt: str, image_path: str, runtime: ToolRuntime) -> Dict[str, Any]:
    """Execute an image edit.

    WHEN TO USE THIS TOOL:
    - When you need to modify an existing image based on recommendations
    - After receiving user instructions to change, enhance, or transform an image
    - When the user requests specific visual changes (e.g., "make brighter",
    "change background", "add elements")

    Args:
        prompt: A clear, descriptive recommendation specifying the desired image edit.
            The recommendation should be specific and actionable.

        image_path: Path to the input image file.

    Returns:
        Dict[str, Any]: A dictionary containing the edit results with the following structure:
            {
                "success": bool,           # True if edit completed successfully
                "image_path": str | None,  # Path to the edited image (in "output/" directory)
                "error": str | None,       # Error message if success is False
                "metadata": Dict           # Additional metadata about the edit operation
            }
    """
    try:
        # Generate output path from tool call id and job id
        job_id = runtime.config["configurable"]["job_id"]
        tool_call_id = runtime.tool_call_id

        output_dir = Path(settings.storage.output_dir) / job_id
        os.makedirs(output_dir, exist_ok=True)

        output_filename = f"edited_{tool_call_id}.png"
        output_path = os.path.join(output_dir, output_filename)

        logger.debug(f"Editing {image_path} for job {job_id}.")
        image = Image.open(image_path)

        strategy = ImageEditingStrategyFactory.create_strategy(settings.image_editing)
        editor = ImageEditor(strategy)
        result = editor.edit(image, prompt, EditParameters(), output_path=output_path)

        # Save to memory using tool_call_id as edit_id
        memory_services[job_id].save_edit_attempt(
            tool_call_id=tool_call_id, prompt=prompt, input_path=result.image_path
        )

        return {
            "success": result.success,
            "image_path": result.image_path,
            "error": result.error_message,
            "metadata": result.metadata or {},
        }
    except Exception as e:
        logger.error(f"Edit execution failed: {e}")
        return {
            "success": False,
            "image_path": None,
            "error": str(e),
            "metadata": {},
            "edit_id": runtime.tool_call_id,
        }


def evaluate_variant(prompt: str, variant_path: str) -> str | Dict[str, Any]:
    """Evaluate an edited image variant against brand guidelines and requirements.

    WHEN TO USE THIS TOOL:
    - When you need to verify that an edited image meets specific brand guidelines,
      design requirements, or quality standards
    - Before presenting a final image to a user, to ensure it meets expectations

    Args:
        prompt: A comprehensive evaluation prompt that provides all context needed
            for the multimodal LLM critic to assess the image. This prompt should include:
            - Brand guidelines (colors, style, tone)
            - Original edit request or recommendations
        variant_path: Path to the generated variant image.

    Returns:
        str: On success, returns the multimodal LLM critic's evaluation as a string.
             This typically contains a score and detailed feedback about how well the
             image meets the specified criteria.

        Dict[str, Any]: On failure, returns an error dictionary with structure:
            {
                "success": False,
                "score": 0.0,
                "feedback": "Error message describing what went wrong"
            }
    """
    try:
        # Verify the image exists and is valid
        Image.open(variant_path).verify()

        # Get strategy from settings
        evaluator = EvaluationStrategyFactory.create_strategy(settings.evaluation)
        result = evaluator.evaluate(variant_path, prompt)

        return result
    except Exception as e:
        error_message = f"Evaluation failed: {e}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "score": 0.0, "feedback": error_message}


def update_memory(
    variant_path: str, score: str, feedback: str, runtime: ToolRuntime
) -> Dict[str, Any]:
    """Update memory with evaluation results for an edited image variant.

    WHEN TO USE THIS TOOL:
    - After evaluating an edited image variant using the evaluate_variant tool
    - To store the critic's score and feedback for future reference and analysis
    - When the refiner needs to access past evaluations to make informed decisions

    Args:
        variant_path: Path to the edited image variant that was evaluated.
            Expected format: data/output/{job_id}/edited_{tool_call_id}.png

        score: The evaluation score returned by the multimodal LLM critic.
            This is typically a string representation of a numeric score.

        feedback: Detailed feedback from the multimodal LLM critic explaining
            the evaluation score and providing insights about how well the
            image meets the specified criteria.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the memory update:
            {
                "success": bool,  # True if memory was updated successfully
                "error": str | None  # Error message if success is False
            }
    """

    def parse_image_path(variant_path: str) -> Tuple[str, str]:
        """Parse job_id and tool_call_id from an image path.

        Expected format: data/output/{job_id}/edited_{tool_call_id}.png

        Args:
            image_path: Path to the edited image

        Returns:
            Tuple of (job_id, tool_call_id)

        Raises:
            ValueError: If the path doesn't match expected format
        """
        path = Path(variant_path)
        filename = path.stem  # e.g., "edited_xDfgTr74jiKlasw"

        # Extract tool_call_id from filename pattern "edited_{tool_call_id}"
        match = re.match(r"edited_(.+)", filename)
        if not match:
            raise ValueError(
                f"Filename '{filename}' doesn't match expected pattern 'edited_{{tool_call_id}}'"
            )

        tool_call_id = match.group(1)
        return tool_call_id

    try:
        # Extract job_id from variant_path or memory location
        # Assuming variant_path is like: data/output/{job_id}/edited_{edit_id}.png
        job_id = runtime.config["configurable"]["job_id"]

        edit_id = parse_image_path(variant_path)

        memory_services[job_id].update_edit_evaluation(
            tool_call_id=edit_id,
            evaluation={
                "score": score,
                "feedback": feedback,
            },
        )

        return {
            "success": True,
        }
    except Exception as e:
        logger.error(f"Memory update failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_memory(runtime: ToolRuntime) -> Dict[str, Any]:
    """Retrieve the complete memory for the current job.

    WHEN TO USE THIS TOOL:
    - When the refiner needs to analyze past edit attempts and evaluations
    - Before proposing refinements to understand what has been tried
    - To identify patterns in successful vs failed edits

    Returns:
        Dict[str, Any]: Complete memory structure with:
            {
                "job_id": str,
                "edit_history": List[Dict],  # All edit attempts with evaluations
            }
    """
    try:
        job_id = runtime.config["configurable"]["job_id"]

        return {
            "success": True,
            "memory": {
                "job_id": job_id,
                "edit_history": memory_services[job_id].get_edit_history(),
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        return {
            "success": False,
            "memory": None,
            "error": str(e),
        }


def generate_report(
    variants: List[Dict[str, Any]], config: RunnableConfig
) -> Dict[str, Any]:
    """Generate a comprehensive report of all generated variants.

    WHEN TO USE THIS TOOL:
    - After completing all variant generation and evaluation iterations
    - When the orchestrator needs to summarize the results of the workflow
    - Before presenting final results to the user

    Args:
        variants: List of variant dictionaries, each containing:
            {
                "variant_id": int,              # Unique variant identifier
                "path": str,                    # Path to the generated variant image
                "recommendation_id": str,       # ID of the recommendation this variant addresses
                "edit_prompt": str,             # The edit prompt used to generate this variant
                "evaluation_score": float,      # Score from evaluation (0-10 or 0-100)
                "evaluation_feedback": str,     # Detailed feedback from the evaluator
                "iterations": int               # Number of iterations to achieve this result
            }

    Returns:
        Dict[str, Any]: Report results with structure:
            {
                "success": bool,                # True if report generated successfully
                "report_path": str | None,      # Path to the generated report file
                "error": str | None,            # Error message if success is False
                "summary": Dict                 # Report summary including:
                    {
                        "total_variants": int,
                        "average_score": float,
                        "best_variant_path": str | None,
                        "best_score": float,
                        "timestamp": str
                    }
            }
    """
    try:
        job_id = config["configurable"]["job_id"]
        # Ensure output directory exists
        output_dir = Path(settings.storage.output_dir) / job_id
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "report.json")

        # Calculate summary statistics
        scores = [v.get("evaluation_score", 0) for v in variants]
        best_variant = (
            max(variants, key=lambda v: v.get("evaluation_score", 0))
            if variants
            else None
        )

        report = {
            "generated_at": datetime.now().isoformat(),
            "variants": variants,
            "summary": {
                "total_variants": len(variants),
                "average_score": sum(scores) / len(scores) if scores else 0.0,
                "best_variant_path": best_variant.get("path") if best_variant else None,
                "best_score": (
                    best_variant.get("evaluation_score") if best_variant else 0.0
                ),
            },
        }

        # Write report to JSON file
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report generated successfully at {output_path} for job {job_id}.")

        return {
            "success": True,
            "report_path": output_path,
            "error": None,
            "summary": report["summary"],
        }

    except Exception as e:
        error_message = f"Report generation failed: {e}"
        logger.error(error_message, exc_info=True)
        return {
            "success": False,
            "report_path": None,
            "error": error_message,
            "summary": {},
        }
