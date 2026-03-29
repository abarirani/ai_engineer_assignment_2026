"""Abstract strategy interface for LLM operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMResult:
    """Result of an LLM operation.

    Attributes:
        success: Whether the operation succeeded.
        error_message: Error message if failed.
        metadata: Additional metadata about the operation.
    """

    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMStrategy(ABC):
    """Abstract base class for LLM strategies.

    This interface defines the contract for all LLM model
    implementations, enabling the strategy pattern for easy extension.
    """

    @abstractmethod
    def get_llm(self) -> Any:
        """Return the LLM client instance.

        Returns:
            The configured LLM client instance (e.g., ChatOpenAI).
        """
        pass
