import os
import time
import logging
from typing import Any, Dict

from PIL import Image

from app.config.settings import settings
from app.services.image_editing.editor import ImageEditor
from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy_factory import ImageEditingStrategyFactory
from app.services.evaluation.strategy_factory import EvaluationStrategyFactory

logger = logging.getLogger(__name__)


def execute_edit(prompt: str, image_path: str) -> Dict[str, Any]:
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
        result = editor.edit(image, prompt, EditParameters(), output_path=output_path)

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
