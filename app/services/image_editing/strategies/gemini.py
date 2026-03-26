"""Google Gemini implementation of the image editing strategy.

This strategy provides image editing capabilities using Google's Gemini API
with image generation/editing capabilities.
"""

import io
import logging

from PIL import Image
from google import genai

from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy import (
    ImageEditResult,
    ImageEditingStrategy,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class GeminiEditingStrategy(ImageEditingStrategy):
    """Google Gemini implementation of the image editing strategy.

    This strategy provides image editing capabilities using Google's Gemini API
    with image generation/editing capabilities.

    Attributes:
        model_name: The Gemini model to use (e.g., 'gemini-2.0-flash').
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
    ):
        """Initialize the Gemini editing strategy.

        Args:
            model_name: The Gemini model to use.
        """
        self.model_name = model_name
        logger.info(f"GeminiEditingStrategy initialized with model: {model_name}")

    def edit_image(
        self,
        image: Image.Image,
        prompt: str,
        parameters: EditParameters,
    ) -> ImageEditResult:
        """Edit image using Google Gemini.

        Args:
            image: The input PIL Image to edit.
            prompt: Text prompt describing the desired edit.
            parameters: Editing parameters (guidance, steps, seed, etc.).

        Returns:
            ImageEditResult containing the edited image or error information.
        """
        try:
            client = genai.Client()

            # Call Gemini API for image editing
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image],
                # config={
                #     "temperature": min(1.0, parameters.guidance_scale / 5.0),
                # },
            )

            # Process response and extract edited image
            edited_image = self._process_response(response)

            return ImageEditResult(
                image=edited_image,
                success=True,
                metadata={
                    "model": self.model_name,
                    "guidance_scale": parameters.guidance_scale,
                    "seed": parameters.seed,
                    "input_size": (image.width, image.height),
                    "output_size": (edited_image.width, edited_image.height),
                },
            )

        except Exception as e:
            logger.error(f"Image editing failed: {e}")
            return ImageEditResult(
                image=None,
                success=False,
                error_message=str(e),
            )

    def _process_response(self, response) -> Image.Image:
        """Process Gemini API response to extract the edited image.

        Args:
            response: The API response object.

        Returns:
            PIL Image of the edited result.
        """
        # Handle different response formats from Gemini API
        # The exact format depends on the specific Gemini model and API version
        if hasattr(response, "parts"):
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    # Handle inline image data
                    image_bytes = part.inline_data.data
                    return Image.open(io.BytesIO(image_bytes))
                elif hasattr(part, "file_data") and part.file_data:
                    # Handle file reference
                    pass

        # Fallback: try to extract image from response text
        if hasattr(response, "text") and response.text:
            logger.warning("No image found in response, got text instead")

        raise ValueError("No image data found in Gemini API response")

    def get_model_info(self) -> ModelInfo:
        """Return information about the Gemini model.

        Returns:
            ModelInfo with name, version, and capabilities.
        """
        return ModelInfo(
            name="Google Gemini",
            version=self.model_name,
            max_resolution=(2048, 2048),
            supported_formats=["PNG", "JPEG", "WEBP"],
        )

    def validate_parameters(self, parameters: EditParameters) -> bool:
        """Validate that parameters are within model constraints.

        Args:
            parameters: The parameters to validate.

        Returns:
            True if parameters are valid, False otherwise.
        """
        info = self.get_model_info()

        # Validate guidance scale (mapped to temperature 0.0-1.0)
        if not 0.1 <= parameters.guidance_scale <= 5.0:
            logger.warning(
                f"guidance_scale {parameters.guidance_scale} out of range [0.1, 5.0]"
            )
            return False

        # Validate dimensions
        width = parameters.width or 64
        height = parameters.height or 64
        if width > info.max_resolution[0] or height > info.max_resolution[1]:
            logger.warning(
                f"Resolution ({width}x{height}) exceeds max {info.max_resolution}"
            )
            return False

        return True
