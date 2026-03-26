"""Mock implementation of the image editing strategy for testing purposes.

This strategy randomly selects an image from the ./output folder and returns it,
providing a simple mock for testing workflows without actual image editing.
"""

import logging
import random
from pathlib import Path

from PIL import Image

from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy import (
    ImageEditResult,
    ImageEditingStrategy,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class MockEditingStrategy(ImageEditingStrategy):
    """Mock implementation of the image editing strategy.

    This strategy randomly selects an image from the ./output folder and returns it,
    providing a simple mock for testing workflows without actual image editing.

    Attributes:
        output_folder: Path to the folder containing mock images.
    """

    def __init__(
        self,
        output_folder: str = "./output",
    ):
        """Initialize the mock editing strategy.

        Args:
            output_folder: Path to the folder containing mock images.
        """
        self.output_folder = Path(output_folder)
        logger.info(
            f"MockEditingStrategy initialized with output folder: {output_folder}"
        )

    def _get_available_images(self) -> list[Path]:
        """Get list of available image files in the output folder.

        Returns:
            List of image file paths in the output folder.
        """
        if not self.output_folder.exists():
            logger.warning(f"Output folder does not exist: {self.output_folder}")
            return []

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        images = [
            f
            for f in self.output_folder.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        return images

    def edit_image(
        self,
        image: Image.Image,
        prompt: str,
        parameters: EditParameters,
    ) -> ImageEditResult:
        """Return a random image from the output folder.

        Args:
            image: The input PIL Image (ignored in mock mode).
            prompt: Text prompt describing the desired edit (ignored in mock mode).
            parameters: Editing parameters (ignored in mock mode).

        Returns:
            ImageEditResult containing a random image from the output folder.
        """
        available_images = self._get_available_images()

        if not available_images:
            logger.error(f"No images found in output folder: {self.output_folder}")
            return ImageEditResult(
                image=None,
                success=False,
                error_message=f"No images found in output folder: {self.output_folder}",
            )

        try:
            # Randomly select an image
            selected_image_path = random.choice(available_images)
            logger.info(f"Mock strategy selected image: {selected_image_path.name}")

            # Open and return the selected image
            selected_image = Image.open(selected_image_path)

            return ImageEditResult(
                image=selected_image,
                image_path=str(selected_image_path),
                success=True,
                metadata={
                    "model": "mock",
                    "selected_image": selected_image_path.name,
                    "total_available": len(available_images),
                    "input_size": (image.width, image.height),
                    "output_size": (selected_image.width, selected_image.height),
                },
            )

        except Exception as e:
            logger.error(f"Mock image selection failed: {e}")
            return ImageEditResult(
                image=None,
                success=False,
                error_message=str(e),
            )

    def get_model_info(self) -> ModelInfo:
        """Return information about the mock model.

        Returns:
            ModelInfo with name, version, and capabilities.
        """
        return ModelInfo(
            name="Mock Editor",
            version="1.0.0",
            max_resolution=(8192, 8192),
            supported_formats=["PNG", "JPEG", "WEBP", "GIF", "BMP"],
        )

    def validate_parameters(self, parameters: EditParameters) -> bool:
        """Always return True since mock strategy doesn't have constraints.

        Args:
            parameters: The parameters to validate.

        Returns:
            True if parameters are valid, False otherwise.
        """
        # Mock strategy accepts all parameters
        return True
