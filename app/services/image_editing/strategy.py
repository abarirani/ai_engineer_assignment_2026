"""Abstract strategy interface for image editing operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

from PIL import Image

from app.services.image_editing.parameters import EditParameters


@dataclass
class ImageEditResult:
    """Result of an image editing operation.

    Attributes:
        image: The edited PIL Image (None if failed).
        image_path: Path to saved image (optional).
        success: Whether the operation succeeded.
        error_message: Error message if failed.
        metadata: Additional metadata about the operation.
    """

    image: Optional[Image.Image] = None
    image_path: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ImageEditingStrategy(ABC):
    """Abstract base class for image editing strategies.

    This interface defines the contract for all image editing model
    implementations, enabling the strategy pattern for easy extension.
    """

    @abstractmethod
    def edit_image(
        self,
        image: Image.Image,
        prompt: str,
        parameters: "EditParameters",
    ) -> ImageEditResult:
        """Edit an image based on the prompt and parameters.

        Args:
            image: The input PIL Image to edit.
            prompt: Text prompt describing the desired edit.
            parameters: Editing parameters (guidance, steps, etc.).

        Returns:
            ImageEditResult containing the edited image or error information.
        """
        pass
