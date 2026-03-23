"""Application configuration settings.

Configuration is loaded from YAML files.
Environment selection is done via APP_ENV environment variable.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def load_yaml_config(yaml_path: Path) -> Dict[str, Any]:
    """Load yaml file.

    Args:
        yaml_path: Path to yaml file.

    Returns:
        Dict: configuration items in yaml file.
    """
    config = {}
    if yaml_path.exists():
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f) or {}
    return config


def load_configs(env: str = "development") -> Dict[str, Any]:
    """Load and merge YAML configuration files.

    Args:
        env: Environment name (development, production, etc.)

    Returns:
        Merged configuration dictionary
    """
    config_dir = Path(__file__).parent
    base_config_path = config_dir / "base.yaml"
    env_config_path = config_dir / f"{env}.yaml"

    base_config = load_yaml_config(base_config_path)
    env_config = load_yaml_config(env_config_path)

    return _deep_merge(base_config, env_config)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Override dictionary

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# Nested models matching YAML structure
class AppSettings(BaseSettings):
    """Application settings."""

    name: str = Field(
        default="Visual Recommendations Agentic Workflow",
        description="Application name",
    )
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")


class ApiSettings(BaseSettings):
    """API settings."""

    v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")


class StorageSettings(BaseSettings):
    """Storage settings."""

    upload_dir: str = Field(default="data/input", description="Upload directory")
    output_dir: str = Field(default="data/output", description="Output directory")


class ProcessingSettings(BaseSettings):
    """Processing settings."""

    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    allowed_file_types: List[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".webp"],
        description="Allowed file types for uploads",
    )
    max_iterations: int = Field(
        default=3, description="Maximum iterations per recommendation"
    )
    processing_timeout_seconds: int = Field(
        default=300, description="Processing timeout in seconds"
    )


class LoggingSettings(BaseSettings):
    """Logging settings."""

    level: str = Field(default="INFO", description="Logging level")


class LLMSettings(BaseSettings):
    """LLM settings."""

    enabled: bool = Field(default=False, description="Whether LLM is enabled")
    provider: str = Field(default="openai_compatible", description="LLM provider type")
    api_key: str = Field(default="", description="API key for LLM provider")
    base_url: str = Field(
        default="http://localhost:11434/v1", description="Base URL for LLM API"
    )
    model_name: str = Field(default="gpt-4o", description="Model name to use")
    temperature: float = Field(default=0.7, description="Temperature for sampling")


class CORSSettings(BaseSettings):
    """CORS settings."""

    allow_origins: List[str] = Field(
        default=["*"], description="Allowed origins for CORS"
    )
    allow_credentials: bool = Field(
        default=True, description="Allow credentials in requests"
    )
    allow_methods: List[str] = Field(default=["*"], description="Allowed HTTP methods")
    allow_headers: List[str] = Field(default=["*"], description="Allowed HTTP headers")


class PromptsSettings(BaseSettings):
    """Prompts settings."""

    deep_agent_system: str = Field(
        default="app/agents/prompts/deep_agent_system_prompt.md",
        description="Path to Deep Agent system prompt markdown file",
    )
    deep_agent_user_message: str = Field(
        default="app/agents/prompts/deep_agent_user_message.jinja2",
        description="Path to Deep Agent user message template jinja2 file",
    )


class ImageEditingSettings(BaseSettings):
    """Image editing settings."""

    enabled: bool = Field(default=True, description="Whether image editing is enabled")
    strategy: str = Field(
        default="klein", description="Editing strategy type (e.g., 'klein')"
    )
    model_path: str = Field(
        default="black-forest-labs/FLUX.2-klein-4B",
        description="Path to the image editing model",
    )
    device: str = Field(
        default="auto",
        description="Device to use for inference ('auto', 'cuda', 'cpu')",
    )
    enable_cpu_offload: bool = Field(
        default=True, description="Enable CPU offloading for VRAM savings"
    )
    dtype: str = Field(
        default="bfloat16",
        description="Data type for model weights ('bfloat16', 'float16', 'float32')",
    )


class EvaluationSettings(BaseSettings):
    """Evaluation settings for multimodal LLM-based evaluation."""

    enabled: bool = Field(default=False, description="Whether evaluation is enabled")
    provider: str = Field(
        default="openai_compatible",
        description="LLM provider type for evaluation (e.g., 'openai_compatible')",
    )
    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for evaluation LLM API",
    )
    model_name: str = Field(
        default="gpt-4o",
        description="Model name for evaluation (must be vision-capable)",
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for evaluation LLM sampling",
    )


class SubagentConfig(BaseSettings):
    """Configuration for a single subagent."""

    description: str = Field(
        default="",
        description="Description of the subagent's role and responsibilities",
    )
    model: str = Field(
        default="anthropic:claude-3-5-sonnet-20241022",
        description="Model to use for this subagent",
    )
    system_prompt: str = Field(
        default="",
        description="System prompt for the subagent",
    )
    tools: List[str] = Field(
        default_factory=list,
        description="List of tools available to this subagent",
    )


class SubagentsSettings(BaseSettings):
    """Subagents configuration that converts to list format for deepagents library."""

    planner: SubagentConfig = Field(
        default_factory=SubagentConfig,
        description="Planner agent configuration",
    )
    editor: SubagentConfig = Field(
        default_factory=SubagentConfig,
        description="Editor agent configuration",
    )
    critic: SubagentConfig = Field(
        default_factory=SubagentConfig,
        description="Critic agent configuration",
    )
    refiner: SubagentConfig = Field(
        default_factory=SubagentConfig,
        description="Refiner agent configuration",
    )

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert subagents to list format expected by create_deep_agent.

        Returns:
            List of subagent configuration dictionaries with name keys.
        """
        return [
            {"name": "planner", **self.planner.model_dump()},
            {"name": "editor", **self.editor.model_dump()},
            {"name": "critic", **self.critic.model_dump()},
            {"name": "refiner", **self.refiner.model_dump()},
        ]


class Settings(BaseSettings):
    """Application settings loaded from YAML configuration files.

    Settings are organized in nested models that mirror the YAML structure.
    """

    # Nested settings matching YAML structure
    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    prompts: PromptsSettings = Field(default_factory=PromptsSettings)
    image_editing: ImageEditingSettings = Field(default_factory=ImageEditingSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    subagents: SubagentsSettings = Field(default_factory=SubagentsSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: BaseSettings,
        env_settings: BaseSettings,
        dotenv_settings: BaseSettings,
        file_secret_settings: BaseSettings,
    ):
        """Customize settings sources to use YAML configuration.

        Environment selection is done via APP_ENV environment variable.
        All other settings are loaded from YAML files.
        """
        env = os.getenv("APP_ENV", "development")
        yaml_config = load_configs(env)

        # Return the nested YAML config directly - Pydantic will map it
        # to the nested models automatically
        return (lambda: yaml_config,)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience instance for direct import
settings = get_settings()
