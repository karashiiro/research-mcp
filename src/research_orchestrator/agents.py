"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
Now implements agents-as-tools pattern for modular research orchestration.
"""

from typing import List
from strands import Agent, tool
from strands.models.model import Model
from .tools import get_research_tools


# System prompts for different agent types
LEAD_RESEARCHER_SYSTEM_PROMPT = """You are a lead researcher who performs three main tasks:
1. Generate JSON lists of research subtopics
2. Delegate research tasks to specialized research agents using available tools
3. Create master synthesis reports

You have access to research_specialist tools that can conduct comprehensive research on any topic.

CRITICAL REQUIREMENTS:
- NEVER generate internal reasoning, thinking, or analysis commentary
- NEVER include reasoning content or signature fields
- Output ONLY the requested content in the specified format
- Be direct, factual, and concise
- Focus on synthesis and organization, not interpretation
- When delegating research, use the research_specialist tool for each subtopic
- Use ONLY information provided in source materials and tool results
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
        # Get research agent tools for the lead researcher (no more global needed!)
        research_agent_tools = get_research_agent_tools(self.model)

        # Create the lead researcher agent with research specialist tools
        self.lead_researcher = Agent(
            model=self.model,
            system_prompt=LEAD_RESEARCHER_SYSTEM_PROMPT,
            tools=research_agent_tools,  # Give lead researcher access to research specialists
        )

        # Create pool of research subagents with web search tools (kept for backward compatibility)
        research_tools = get_research_tools()
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


# Agent-as-Tools Implementation
def create_research_specialist_tool(model: Model):
    """
    Factory function that creates a research specialist tool with model closure.

    Args:
        model: The model instance to use for the research agent

    Returns:
        A research specialist tool function bound with the provided model
    """

    @tool
    def research_specialist(query: str) -> str:
        """
        Specialized research agent that conducts comprehensive web searches and analysis.

        Args:
            query: The research topic or question to investigate

        Returns:
            Comprehensive research report with findings and citations
        """
        research_agent = Agent(
            model=model,
            system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
            tools=get_research_tools(),
        )

        prompt = f"""What current information can you find about "{query}"? Please search for details and provide a comprehensive overview with sources."""

        try:
            response = research_agent(prompt)
            # Extract text content from response
            from .orchestrator import extract_content_text

            return "".join(map(extract_content_text, response.message["content"]))
        except Exception as e:
            return f"Research failed for '{query}': {str(e)}"

    return research_specialist


def get_research_agent_tools(model: Model) -> List:
    """
    Get the list of research agent tools for the lead researcher.

    Args:
        model: The model instance to create tools with

    Returns:
        List of specialized research agent tools bound with the provided model
    """
    return [create_research_specialist_tool(model)]
