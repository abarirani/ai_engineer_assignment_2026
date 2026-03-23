"""Image editor facade that uses a strategy for the actual editing."""

import logging
import os

from PIL import Image

from .parameters import EditParameters
from .strategy import ImageEditingStrategy, ImageEditResult

logger = logging.getLogger(__name__)


class ImageEditor:
    """Image editor that uses a strategy for the actual editing.

    This class provides a clean interface for image editing while
    delegating the model-specific logic to the strategy. It supports
    runtime strategy switching for flexibility.

    Attributes:
        _strategy: The current editing strategy implementation.
    """

    def __init__(self, strategy: ImageEditingStrategy):
        """Initialize the image editor with a strategy.

        Args:
            strategy: The editing strategy to use (e.g., KleinEditingStrategy).
        """
        self._strategy = strategy
        logger.info(
            f"ImageEditor initialized with strategy: {strategy.__class__.__name__}"
        )

    def edit(
        self,
        image: Image.Image,
        prompt: str,
        parameters: EditParameters,
        output_path: str,
    ) -> ImageEditResult:
        """Edit an image using the current strategy.

        Args:
            image: The input PIL Image to edit.
            prompt: Text prompt describing the desired edit.
            parameters: Editing parameters.
            output_path: Path to save the edited image.

        Returns:
            ImageEditResult containing the edited image or error information.
        """
        if not self._strategy.validate_parameters(parameters):
            logger.warning("Invalid parameters for current model")
            return ImageEditResult(
                image=None,
                success=False,
                error_message="Invalid parameters for current model",
            )

        logger.debug(f"Editing image with prompt: {prompt[:50]}...")
        result = self._strategy.edit_image(image, prompt, parameters)

        if result.success:
            logger.info("Image edit completed successfully")
            # Save the edited image
            if result.image is not None:
                try:
                    output_dir = os.path.dirname(output_path)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                    result.image.save(output_path)
                    result.image_path = output_path
                    logger.info(f"Edited image saved to: {output_path}")
                except Exception as e:
                    logger.error(f"Failed to save edited image to {output_path}: {e}")
                    result.error_message = f"Edit succeeded but save failed: {e}"
        else:
            logger.error(f"Image edit failed: {result.error_message}")

        return result
