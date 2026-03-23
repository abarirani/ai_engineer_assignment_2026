"""Factory for creating image editing strategies based on configuration."""

import logging
from typing import Dict, Type

import torch

from app.config.settings import ImageEditingSettings

from .strategy import ImageEditingStrategy
from .strategies.klein import KleinEditingStrategy

logger = logging.getLogger(__name__)


class ImageEditingStrategyFactory:
    """Factory for creating image editing strategies based on configuration.

    This factory pattern allows for easy extension with new editing strategies
    without modifying the code that uses them. New strategies can be added
    by registering them in the _strategies dictionary.

    Attributes:
        _strategies: Mapping of strategy names to strategy classes.
    """

    _strategies: Dict[str, Type[ImageEditingStrategy]] = {
        "klein": KleinEditingStrategy,
        # Add more strategies here as they are implemented
    }

    @classmethod
    def _parse_dtype(cls, dtype_str: str) -> torch.dtype:
        """Parse a dtype string into a torch.dtype.

        Args:
            dtype_str: String representation of the dtype.

        Returns:
            torch.dtype: The corresponding torch data type.

        Raises:
            ValueError: If the dtype string is not recognized.
        """
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
            "fp32": torch.float32,
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
        }
        dtype_lower = dtype_str.lower()
        if dtype_lower not in dtype_map:
            raise ValueError(
                f"Unknown dtype: {dtype_str}. "
                f"Supported dtypes: {', '.join(dtype_map.keys())}"
            )
        return dtype_map[dtype_lower]

    @classmethod
    def _parse_device(cls, device_str: str) -> str | None:
        """Parse a device string into a device specification.

        Args:
            device_str: String representation of the device.

        Returns:
            str | None: The device string, or None for auto-detection.
        """
        if device_str.lower() == "auto":
            return None
        return device_str

    @classmethod
    def create_strategy(
        cls, settings: ImageEditingSettings
    ) -> ImageEditingStrategy:
        """Create an editing strategy based on settings.

        This method instantiates the appropriate editing strategy class
        based on the configuration provided in the settings object.

        Args:
            settings: ImageEditingSettings object containing strategy configuration.

        Returns:
            ImageEditingStrategy: An instance of the configured strategy.

        Raises:
            ValueError: If the strategy type is not recognized.
        """
        strategy_class = cls._strategies.get(settings.strategy)
        if strategy_class is None:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown editing strategy: {settings.strategy}. "
                f"Available strategies: {available}"
            )

        logger.info(f"Creating editing strategy: {settings.strategy}")

        strategy = strategy_class(
            model_path=settings.model_path,
            device=cls._parse_device(settings.device),
            dtype=cls._parse_dtype(settings.dtype),
            enable_cpu_offload=settings.enable_cpu_offload,
        )

        logger.info(f"Editing strategy '{settings.strategy}' created successfully")
        return strategy

    @classmethod
    def register_strategy(
        cls, name: str, strategy_class: Type[ImageEditingStrategy]
    ) -> None:
        """Register a new editing strategy.

        This method allows dynamic registration of new strategies at runtime.

        Args:
            name: The name to use for this strategy in configuration.
            strategy_class: The strategy class to register.
        """
        cls._strategies[name] = strategy_class
        logger.info(f"Registered editing strategy: {name}")

    @classmethod
    def get_available_strategies(cls) -> list[str]:
        """Get a list of available strategy names.

        Returns:
            list[str]: List of registered strategy names.
        """
        return list(cls._strategies.keys())
