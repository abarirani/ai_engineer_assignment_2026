"""Parameters for image editing operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EditParameters:
    """Parameters for image editing operations.

    This dataclass encapsulates all configurable parameters for image
    editing operations, providing a clean interface for parameter management.
    """

    guidance_scale: float = 1.0
    num_inference_steps: int = 4
    seed: Optional[int] = None
    height: Optional[int] = None
    width: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the parameters.
        """
        return {
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
            "seed": self.seed,
            "height": self.height,
            "width": self.width,
        }
