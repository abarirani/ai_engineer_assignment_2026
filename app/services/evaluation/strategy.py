"""Abstract strategy interface for evaluation operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EvaluationResult:
    """Result of an evaluation operation.

    Attributes:
        score: Evaluation score (0.0 to 1.0).
        feedback: Detailed feedback in markdown format.
        success: Whether the operation succeeded.
        error_message: Error message if failed.
        metadata: Additional metadata about the evaluation.
    """

    score: float = 0.0
    feedback: str = ""
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EvaluationStrategy(ABC):
    """Abstract base class for evaluation strategies.

    This interface defines the contract for all evaluation model
    implementations, enabling the strategy pattern for easy extension.
    """

    @abstractmethod
    def evaluate(
        self,
        image_path: str,
        prompt: str,
    ) -> EvaluationResult:
        """Evaluate an image variant using the provided prompt.

        Args:
            image_path: Path to the image to evaluate.
            prompt: The evaluation prompt containing all context (recommendation, brand guidelines, etc.).

        Returns:
            EvaluationResult containing score, feedback, and metadata.
        """
        pass
