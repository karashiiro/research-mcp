"""
Model Provider Abstractions and Factory

Provides model creation and abstractions for different providers.
"""

import os
from strands.models.bedrock import BedrockModel
from strands.models.model import Model
from strands.models.ollama import OllamaModel
from typing import Dict, Optional, Any


class ModelFactory:
    """Factory for creating model instances based on configuration."""

    @staticmethod
    def create_model(
        model_type: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
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
        temperature: float, max_tokens: Optional[int] = None, **kwargs
    ) -> BedrockModel:
        """Create a Bedrock model instance."""
        config = {
            "model_id": os.getenv("BEDROCK_MODEL", "openai.gpt-oss-20b-1:0"),
            "temperature": temperature,
            "max_tokens": max_tokens or 6000,
        }
        config.update(kwargs)
        return BedrockModel(**config)  # type: ignore[arg-type]

    @staticmethod
    def get_supported_providers() -> Dict[str, str]:
        """Get list of supported model providers."""
        return {"ollama": "Local Ollama server", "bedrock": "AWS Bedrock service"}


def create_model(**kwargs) -> Model:
    """Convenience function to create a model using the factory."""
    return ModelFactory.create_model(**kwargs)
