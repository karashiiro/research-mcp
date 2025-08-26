"""
Simplified Application Settings

Centralized configuration using Pydantic Settings for type safety and validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and type safety."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required settings
    brave_api_key: str

    # Model settings
    model_type: Literal["ollama", "bedrock"] = "bedrock"
    model_temperature: float = 0.0

    # Bedrock settings
    bedrock_model: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    bedrock_subagent_models: str = ""

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"

    @property
    def bedrock_subagent_models_list(self) -> list[str]:
        """Get bedrock_subagent_models as a parsed list."""
        if not self.bedrock_subagent_models:
            return []
        return [
            model.strip()
            for model in self.bedrock_subagent_models.split(",")
            if model.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore
