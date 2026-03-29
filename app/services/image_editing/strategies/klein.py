"""FLUX.2 [klein] 4B implementation of the image editing strategy."""

import logging
from typing import Optional

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

from app.services.image_editing.parameters import EditParameters
from app.services.image_editing.strategy import ImageEditResult, ImageEditingStrategy

logger = logging.getLogger(__name__)


class KleinEditingStrategy(ImageEditingStrategy):
    """FLUX.2 [klein] 4B implementation of the image editing strategy.

    This strategy provides image editing capabilities using the FLUX.2 [klein]
    model, which offers sub-second inference on consumer GPUs.

    Attributes:
        model_path: Path to the model checkpoint.
        device: Device to run inference on ('cuda' or 'cpu').
        dtype: Data type for model weights.
        enable_cpu_offload: Whether to enable CPU offloading for VRAM savings.
        pipeline: The Flux2KleinPipeline instance (initialized lazily).
        _initialized: Flag indicating if the pipeline has been initialized.
    """

    def __init__(
        self,
        model_path: str = "black-forest-labs/FLUX.2-klein-4B",
        device: Optional[str] = None,
        dtype: torch.dtype = torch.bfloat16,
        enable_cpu_offload: bool = True,
    ):
        """Initialize the Klein editing strategy.

        Args:
            model_path: Path to the FLUX.2 [klein] model checkpoint.
            device: Device to run inference on (auto-detects if None).
            dtype: Data type for model weights (default: bfloat16).
            enable_cpu_offload: Whether to enable CPU offloading for VRAM savings.
        """
        self.model_path = model_path
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = dtype
        self.enable_cpu_offload = enable_cpu_offload
        self.pipeline: Optional[Flux2KleinPipeline] = None
        self._initialized = False
        logger.info(f"KleinEditingStrategy initialized with model: {model_path}")

    def _ensure_initialized(self) -> None:
        """Lazy initialization of the pipeline.

        This method ensures the pipeline is loaded only when needed,
        deferring GPU memory allocation until the first edit operation.
        """
        if not self._initialized:
            logger.info(f"Loading FLUX.2 [klein] model from {self.model_path}")
            self.pipeline = Flux2KleinPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
            )
            if self.enable_cpu_offload:
                self.pipeline.enable_model_cpu_offload()
                logger.info("CPU offloading enabled for VRAM savings")
            self._initialized = True
            logger.info("FLUX.2 [klein] model loaded successfully")

    def edit_image(
        self,
        image: Image.Image,
        prompt: str,
        parameters: EditParameters,
    ) -> ImageEditResult:
        """Edit image using FLUX.2 [klein].

        Args:
            image: The input PIL Image to edit.
            prompt: Text prompt describing the desired edit.
            parameters: Editing parameters (guidance, steps, seed, etc.).

        Returns:
            ImageEditResult containing the edited image or error information.
        """
        self._ensure_initialized()

        try:
            # Create generator with seed
            generator = torch.Generator(device=self.device).manual_seed(
                parameters.seed if parameters.seed is not None else 0
            )

            # Execute the edit
            result = self.pipeline(
                image=image,
                prompt=prompt,
                height=parameters.height or image.height,
                width=parameters.width or image.width,
                guidance_scale=parameters.guidance_scale,
                num_inference_steps=parameters.num_inference_steps,
                generator=generator,
            )

            edited_image = result.images[0]

            return ImageEditResult(
                image=edited_image,
                success=True,
                metadata={
                    "model": "flux2-klein-4b",
                    "guidance_scale": parameters.guidance_scale,
                    "inference_steps": parameters.num_inference_steps,
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
