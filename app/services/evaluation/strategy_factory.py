"""Factory for creating evaluation strategies based on configuration."""

import logging
from typing import Dict, Type

from app.config.settings import EvaluationSettings

from app.services.evaluation.strategy import EvaluationStrategy
from app.services.evaluation.strategies.multimodal_openai_critic import (
    OpenAICompatibleMultimodalCriticStrategy,
)

logger = logging.getLogger(__name__)


class EvaluationStrategyFactory:
    """Factory for creating evaluation strategies based on configuration.

    This factory pattern allows for easy extension with new evaluation strategies
    without modifying the code that uses them. New strategies can be added
    by registering them in the _strategies dictionary.

    Attributes:
        _strategies: Mapping of strategy names to strategy classes.
    """

    _strategies: Dict[str, Type[EvaluationStrategy]] = {
        "openai_compatible": OpenAICompatibleMultimodalCriticStrategy,
    }

    @classmethod
    def create_strategy(cls, settings: EvaluationSettings) -> EvaluationStrategy:
        """Create an evaluation strategy based on settings.

        This method instantiates the appropriate evaluation strategy class
        based on the provider configuration provided in the settings object.

        Args:
            settings: EvaluationSettings object containing provider configuration.

        Returns:
            EvaluationStrategy: An instance of the configured strategy.

        Raises:
            ValueError: If the provider type is not recognized.
        """
        strategy_class = cls._strategies.get(settings.provider)
        if strategy_class is None:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown evaluation provider: {settings.provider}. "
                f"Available providers: {available}"
            )

        logger.debug(f"Creating evaluation strategy for provider: {settings.provider}")
        return strategy_class(settings)
