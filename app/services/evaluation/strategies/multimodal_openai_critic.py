"""Multimodal LLM-based evaluation strategy using OpenAI-compatible models."""

import base64
import logging
from io import BytesIO
from typing import Any

from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.config.settings import EvaluationSettings
from app.services.evaluation.strategy import EvaluationResult, EvaluationStrategy

logger = logging.getLogger(__name__)


class OpenAICompatibleMultimodalCriticStrategy(EvaluationStrategy):
    """Evaluation strategy using a multimodal LLM as a critic.

    This strategy uses a vision-capable LLM (e.g., gpt-4o) to evaluate
    image variants by sending the image as base64-encoded content along
    with the evaluation prompt.
    """

    def __init__(self, evaluation_settings: EvaluationSettings):
        """Initialize the multimodal critic strategy.

        Args:
            evaluation_settings: EvaluationSettings object containing provider configuration.
        """
        self._settings = evaluation_settings
        self._llm_instance: Any = None

    def _get_llm(self) -> Any:
        """Get the LLM instance for evaluation.

        Returns:
            The configured LLM client instance.
        """
        if self._llm_instance is None:
            eval_config = self._settings
            self._llm_instance = ChatOpenAI(
                base_url=eval_config.base_url,
                model_name=eval_config.model_name,
                temperature=eval_config.temperature,
            )
        return self._llm_instance

    def _image_to_base64(self, image_path: str) -> str:
        """Convert an image file to base64 data URL.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64-encoded data URL string.
        """
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            base64_bytes = base64.b64encode(buffer.getvalue())
            base64_string = base64_bytes.decode("utf-8")
            return f"data:image/png;base64,{base64_string}"

    def evaluate(
        self,
        image_path: str,
        prompt: str,
    ) -> EvaluationResult | str | list[str | dict]:
        """Evaluate an image variant using the multimodal LLM critic.

        Args:
            image_path: Path to the image to evaluate.
            prompt: The evaluation prompt containing all context.

        Returns:
            EvaluationResult containing score, feedback, and metadata.
        """
        # Convert image to base64
        image_b64 = self._image_to_base64(image_path)

        # Invoke multimodal LLM with image
        llm = self._get_llm()
        response = llm.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_b64}},
                    ]
                )
            ]
        )

        # Parse the response content as JSON
        return response.content

    def validate_configuration(self) -> bool:
        """Validate that the evaluation configuration is valid.

        Checks that all required configuration values are present and valid:
        - base_url is set and non-empty
        - model_name is set and non-empty
        - temperature is a valid float between 0 and 1

        Returns:
            True if configuration is valid, False otherwise.
        """
        try:
            eval_config = self._settings

            # Check base_url
            if not eval_config.base_url or not isinstance(eval_config.base_url, str):
                logger.error("Evaluation base_url is not configured properly")
                return False

            # Check model_name
            if not eval_config.model_name or not isinstance(
                eval_config.model_name, str
            ):
                logger.error("Evaluation model_name is not configured properly")
                return False

            # Check temperature is a valid float
            if not isinstance(eval_config.temperature, (int, float)):
                logger.error("Evaluation temperature must be a numeric value")
                return False

            if not (0 <= eval_config.temperature <= 1):
                logger.error("Evaluation temperature must be between 0 and 1")
                return False

            logger.debug("Evaluation configuration validated successfully")
            return True
        except Exception as e:
            logger.error(f"Error validating evaluation configuration: {e}")
            return False
