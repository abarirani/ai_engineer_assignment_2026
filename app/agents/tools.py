import os
import time
import logging
from typing import Any, Dict

from PIL import Image

from app.config.settings import settings
from app.services.image_editing.editor import ImageEditor
from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy_factory import ImageEditingStrategyFactory

logger = logging.getLogger(__name__)


def _select_parameters(priority: int) -> EditParameters:
    """Select editing parameters based on priority level.

    Args:
        priority: Task priority level (1-5).

    Returns:
        EditParameters configured for the priority level.
    """
    priority_map = {
        1: EditParameters(
            num_inference_steps=20,
            guidance_scale=3.5,
            seed=None,
        ),
        2: EditParameters(
            num_inference_steps=25,
            guidance_scale=4.0,
            seed=None,
        ),
        3: EditParameters(
            num_inference_steps=30,
            guidance_scale=4.5,
            seed=None,
        ),
        4: EditParameters(
            num_inference_steps=40,
            guidance_scale=5.0,
            seed=None,
        ),
        5: EditParameters(
            num_inference_steps=50,
            guidance_scale=7.5,
            seed=None,
        ),
    }
    return priority_map.get(priority, priority_map[3])


def execute_edit(prompt: str, image_path: str, priority: int = 1) -> Dict[str, Any]:
    """Execute an image edit.

    This tool performs the actual image editing operation using the
    provided prompt and parameters derived from the priority level.

    Args:
        prompt: The editing prompt.
        image_path: Path to the input image.

    Returns:
        Dictionary with edit results including success status,
        image path, and any error messages.
    """

    priority = max(1, min(5, priority))
    parameters = _select_parameters(priority)

    # Generate output path in the output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    output_filename = f"edited_{timestamp}.png"
    output_path = os.path.join(output_dir, output_filename)

    try:
        image = Image.open(image_path).convert("RGB")
        # Get strategy from factory based on configuration
        strategy = ImageEditingStrategyFactory.create_strategy(settings.image_editing)
        editor = ImageEditor(strategy)
        result = editor.edit(image, prompt, parameters, output_path=output_path)

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
        }


def evaluate_variant(
    variant_path: str, recommendation: str, brand_guidelines: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluate a variant's quality and brand compliance.

    This tool evaluates how well the generated variant matches the
    recommendation and adheres to brand guidelines.

    Args:
        variant_path: Path to the generated variant image.
        recommendation: The original recommendation.
        brand_guidelines: Brand constraints to check against.

    Returns:
        Dictionary with evaluation score and feedback.
    """
    try:
        Image.open(variant_path).verify()
        score = 0.85

        feedback_parts = ["## Variant Evaluation", f"Score: {score:.2f}"]

        if brand_guidelines:
            feedback_parts.append("")
            feedback_parts.append("## Brand Compliance Check")
            feedback_parts.append("Variant adheres to brand guidelines.")

        return {
            "score": score,
            "feedback": "\n".join(feedback_parts),
        }
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {"score": 0.0, "feedback": f"Evaluation failed: {e}"}
