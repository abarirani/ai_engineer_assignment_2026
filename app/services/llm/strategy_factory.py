"""Factory for creating LLM strategies based on configuration."""

import logging
from typing import Dict, Type

from app.config.settings import LLMSettings

from app.services.llm.strategy import LLMStrategy
from app.services.llm.strategies.openai_compatible import OpenAICompatibleStrategy

logger = logging.getLogger(__name__)


class LLMStrategyFactory:
    """Factory for creating LLM strategies based on configuration.

    This factory pattern allows for easy extension with new LLM strategies
    without modifying the code that uses them. New strategies can be added
    by registering them in the _strategies dictionary.

    Attributes:
        _strategies: Mapping of provider names to strategy classes.
    """

    _strategies: Dict[str, Type[LLMStrategy]] = {
        "openai_compatible": OpenAICompatibleStrategy,
        # Add more strategies here as they are implemented
        # Example: "anthropic": AnthropicStrategy,
        # Example: "azure": AzureStrategy,
    }

    @classmethod
    def create_strategy(cls, settings: LLMSettings) -> LLMStrategy:
        """Create an LLM strategy based on settings.

        This method instantiates the appropriate LLM strategy class
        based on the provider configuration provided in the settings object.

        Args:
            settings: LLMSettings object containing provider configuration.

        Returns:
            LLMStrategy: An instance of the configured strategy.

        Raises:
            ValueError: If the provider type is not recognized.
        """
        strategy_class = cls._strategies.get(settings.provider)
        if strategy_class is None:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown LLM provider: {settings.provider}. "
                f"Available providers: {available}"
            )

        logger.debug(f"Creating LLM strategy for provider: {settings.provider}")
        return strategy_class(settings)

    @classmethod
    def register_strategy(
        cls, provider_name: str, strategy_class: Type[LLMStrategy]
    ) -> None:
        """Register a new LLM strategy provider.

        This method allows dynamic registration of new LLM strategies
        at runtime.

        Args:
            provider_name: The name of the provider (e.g., "openai_compatible").
            strategy_class: The strategy class to register.

        Raises:
            ValueError: If the strategy class does not implement LLMStrategy.
        """
        if not issubclass(strategy_class, LLMStrategy):
            raise ValueError(
                f"Strategy class {strategy_class.__name__} must implement LLMStrategy"
            )

        cls._strategies[provider_name] = strategy_class
        logger.info(f"Registered LLM strategy provider: {provider_name}")

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get a list of available LLM provider names.

        Returns:
            List of provider names that are currently registered.
        """
        return list(cls._strategies.keys())
