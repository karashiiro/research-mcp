"""
Model Provider Abstractions and Factory

Provides model creation and abstractions for different providers.
"""

import os

from botocore.config import Config as BotocoreConfig
from strands.models.bedrock import BedrockModel
from strands.models.model import Model
from strands.models.ollama import OllamaModel


class ModelFactory:
    """Factory for creating model instances based on configuration."""

    @staticmethod
    def create_model(
        model_type: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> Model:
        """
        Create a model instance based on configuration.

        Args:
            model_type: Type of model to create ("ollama" or "bedrock")
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens for generation
            **kwargs: Additional model-specific parameters

        Returns:
            Configured model instance
        """
        # Use environment defaults if not provided
        model_type = model_type or os.getenv("MODEL_TYPE", "bedrock")
        temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("MODEL_TEMPERATURE", 0.0))
        )

        if model_type == "ollama":
            return ModelFactory._create_ollama_model(temperature, **kwargs)
        else:
            return ModelFactory._create_bedrock_model(temperature, max_tokens, **kwargs)

    @staticmethod
    def create_model_with_id(
        model_id: str,
        model_type: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> Model:
        """
        Create a model instance with a specific model ID.

        Args:
            model_id: Specific model ID to use (e.g., "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
            model_type: Type of model to create ("ollama" or "bedrock")
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum tokens for generation
            **kwargs: Additional model-specific parameters

        Returns:
            Configured model instance
        """
        # Use environment defaults if not provided
        model_type = model_type or os.getenv("MODEL_TYPE", "bedrock")
        temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("MODEL_TEMPERATURE", 0.0))
        )

        if model_type == "ollama":
            # For Ollama, pass model_id as model parameter
            return ModelFactory._create_ollama_model(
                temperature, model=model_id, **kwargs
            )
        else:
            # For Bedrock, pass model_id directly
            return ModelFactory._create_bedrock_model(
                temperature, max_tokens, model_id=model_id, **kwargs
            )

    @staticmethod
    def _create_ollama_model(temperature: float, **kwargs) -> OllamaModel:
        """Create an Ollama model instance."""
        config = {
            "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "model_id": os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            "temperature": temperature,
        }
        config.update(kwargs)
        return OllamaModel(**config)  # type: ignore[arg-type]

    @staticmethod
    def _create_bedrock_model(
        temperature: float,
        max_tokens: int | None = None,
        model_id: str | None = None,
        **kwargs,
    ) -> BedrockModel:
        """Create a Bedrock model instance with model-specific token limits and retry config."""
        final_model_id = model_id or os.getenv(
            "BEDROCK_MODEL", "openai.gpt-oss-20b-1:0"
        )

        # Set appropriate max_tokens based on model capabilities
        # Claude 3.5 Sonnet has 8192 output token limit
        if max_tokens is None:
            if final_model_id and "claude-3-5-sonnet" in final_model_id:
                max_tokens = 8000  # Safe limit for Claude 3.5 Sonnet (8192 limit)
            else:
                max_tokens = 10000  # Default for other Claude models

        # Create boto3 client config with exponential backoff for throttling mitigation
        # Based on research findings: adaptive retry mode with up to 10 attempts
        # aligns retries to 60-second quota windows and includes random jitter
        boto_config = BotocoreConfig(
            retries={
                "max_attempts": 10,  # Increase from default 4 to handle throttling
                "mode": "adaptive",  # Use adaptive retry with exponential backoff + jitter
            },
            connect_timeout=30,  # Increase connection timeout for reliability
            read_timeout=120,  # Increase read timeout for long generations
        )

        config = {
            "model_id": final_model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": True
            if final_model_id and "claude" in final_model_id
            else False,  # Required for some models to avoid tool use issues
            "cache_prompt": "default"
            if final_model_id and "claude" in final_model_id
            else None,
            "boto_client_config": boto_config,  # Add retry configuration
        }
        config.update(kwargs)
        return BedrockModel(**config)  # type: ignore[arg-type]

    @staticmethod
    def get_supported_providers() -> dict[str, str]:
        """Get list of supported model providers."""
        return {"ollama": "Local Ollama server", "bedrock": "AWS Bedrock service"}


def create_model(**kwargs) -> Model:
    """Convenience function to create a model using the factory."""
    return ModelFactory.create_model(**kwargs)
