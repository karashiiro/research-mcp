"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
"""

from typing import List
from strands import Agent
from strands.models.model import Model
from .tools import get_research_tools


# System prompts for different agent types
LEAD_RESEARCHER_SYSTEM_PROMPT = """You are a lead researcher who performs two main tasks:
1. Generate JSON lists of research subtopics
2. Create master synthesis reports

CRITICAL REQUIREMENTS:
- NEVER generate internal reasoning, thinking, or analysis commentary
- NEVER include reasoning content or signature fields
- Output ONLY the requested content in the specified format
- Be direct, factual, and concise
- Focus on synthesis and organization, not interpretation
- Use ONLY information provided in source materials
- Maintain consistent formatting and structure"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a research agent. When given a research topic, search for current information and create a detailed research report.

Use your web search capabilities to find comprehensive information about the topic, then write a properly formatted research report with citations."""


class AgentManager:
    """Manages creation and coordination of research agents."""

    def __init__(self, model: Model, num_subagents: int = 5):
        """
        Initialize the agent manager.

        Args:
            model: Model instance to use for all agents
            num_subagents: Number of research subagents to create
        """
        self.model = model
        self.num_subagents = num_subagents
        self.lead_researcher = None
        self.subagents: List[Agent] = []

        self._create_agents()

    def _create_agents(self):
        """Create lead researcher and subagent pool."""
        # Get research tools for agents
        research_tools = get_research_tools()

        # Create the lead researcher agent (no tools needed for synthesis)
        self.lead_researcher = Agent(
            model=self.model,
            system_prompt=LEAD_RESEARCHER_SYSTEM_PROMPT,
        )

        # Create pool of research subagents with web search tools
        self.subagents = []
        for _ in range(self.num_subagents):
            self.subagents.append(
                Agent(
                    model=self.model,
                    system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
                    tools=research_tools,  # Give subagents direct web search access
                )
            )

    def get_lead_researcher(self) -> Agent:
        """Get the lead researcher agent."""
        assert self.lead_researcher
        return self.lead_researcher

    def get_subagent(self, agent_id: int) -> Agent:
        """Get a specific subagent by ID."""
        return self.subagents[agent_id % len(self.subagents)]

    def get_all_subagents(self) -> List[Agent]:
        """Get all subagents."""
        return self.subagents

    def get_agent_count(self) -> int:
        """Get total number of subagents."""
        return len(self.subagents)


def create_agent_manager(model: Model, num_subagents: int = 5) -> AgentManager:
    """Convenience function to create an agent manager."""
    return AgentManager(model, num_subagents)
