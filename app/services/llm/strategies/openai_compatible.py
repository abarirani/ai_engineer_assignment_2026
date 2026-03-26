"""OpenAI-compatible LLM strategy implementation."""

from typing import Any

from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.services.llm.strategy import LLMStrategy


class OpenAICompatibleStrategy(LLMStrategy):
    """Strategy for OpenAI-compatible LLM providers.

    This strategy creates and configures a ChatOpenAI client based on
    the settings from the YAML configuration file.
    """

    def __init__(self):
        """Initialize the OpenAI-compatible LLM strategy."""
        self._settings = settings.llm
        self._llm_instance: Any = None

    def get_llm(self) -> ChatOpenAI:
        """Return the ChatOpenAI client instance.

        Creates and returns a ChatOpenAI instance configured with
        settings from the YAML config file.

        Returns:
            ChatOpenAI: Configured ChatOpenAI client instance.
        """
        if self._llm_instance is None:
            llm_config = self._settings
            self._llm_instance = ChatOpenAI(
                base_url=llm_config.base_url,
                model_name=llm_config.model_name,
                temperature=llm_config.temperature,
            )
        return self._llm_instance

    def validate_configuration(self) -> bool:
        """Validate that the LLM configuration is valid.

        Checks that required configuration values are present.

        Returns:
            True if configuration is valid, False otherwise.
        """
        llm_config = self._settings.llm

        # Check if LLM is enabled
        if not llm_config.enabled:
            return False

        if not llm_config.base_url:
            return False

        if not llm_config.model_name:
            return False

        return True
