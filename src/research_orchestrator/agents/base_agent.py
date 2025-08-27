"""
Base agent functionality and common utilities.
"""

from strands import Agent
from strands.models.model import Model


class BaseAgent:
    """Base class for all research agents providing common functionality."""

    def __init__(self, model: Model, system_prompt: str, tools: list | None = None):
        """
        Initialize base agent.

        Args:
            model: Model instance for this agent
            system_prompt: System prompt defining agent behavior
            tools: Optional list of tools for this agent
        """
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.agent = Agent(
            model=model,
            system_prompt=system_prompt,
            tools=self.tools,
        )

    def __call__(self, prompt: str):
        """Make the agent callable."""
        return self.agent(prompt)
