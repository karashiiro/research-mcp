"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
Now implements agents-as-tools pattern for modular research orchestration.
"""

from typing import List, Optional
import asyncio
import time
import uuid
import os
from strands import Agent, tool
from strands.models.model import Model
from .tools import get_research_tools
from .models import ModelFactory


# System prompts for different agent types
LEAD_RESEARCHER_SYSTEM_PROMPT = """You are a lead researcher who performs three main tasks:
1. Generate JSON lists of research subtopics
2. Delegate research tasks to specialized research agents using available tools
3. Create master synthesis reports

You have access to research_specialist tools that conduct concurrent research for maximum efficiency.

CRITICAL REQUIREMENTS:
- NEVER generate internal reasoning, thinking, or analysis commentary
- NEVER include reasoning content or signature fields
- Output ONLY the requested content in the specified format
- Be direct, factual, and concise
- Focus on synthesis and organization, not interpretation
- The research_specialist tool ONLY accepts lists of queries and returns lists of reports
- Always provide ALL subtopics as a single list to research_specialist for concurrent processing
- Use ONLY information provided in source materials and tool results
- Maintain consistent formatting and structure"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a research agent. When given a research topic, search for current information and create a detailed research report.

Use your web search capabilities to find comprehensive information about the topic, then write a properly formatted research report with citations."""


class AgentManager:
    """Manages creation and coordination of research agents with hybrid model support."""

    def __init__(
        self,
        model: Model,
        num_subagents: int = 5,
        subagent_model_pool: Optional[List[str]] = None,
    ):
        """
        Initialize the agent manager with support for hybrid model pools.

        Args:
            model: Model instance to use for lead researcher
            num_subagents: Number of research subagents to create
            subagent_model_pool: Optional list of model IDs for subagents. If None, uses main model.
        """
        self.model = model  # Lead researcher model
        self.num_subagents = num_subagents
        self.subagent_model_pool = subagent_model_pool or []
        self.lead_researcher = None
        self.subagents: List[Agent] = []
        self.subagent_models: List[Model] = []  # Store created subagent models

        self._create_agents()

    def _create_agents(self):
        """Create lead researcher and hybrid subagent pool."""
        # Create subagent models from pool first
        self._create_subagent_models()

        # Create pool of research subagents with web search tools
        research_tools = get_research_tools()
        self.subagents = []
        for i in range(self.num_subagents):
            # Use different models for each subagent
            subagent_model = self.subagent_models[i % len(self.subagent_models)]
            self.subagents.append(
                Agent(
                    model=subagent_model,
                    system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
                    tools=research_tools,  # Give subagents direct web search access
                )
            )

        # NOW create research agent tools using THIS AgentManager instance
        research_agent_tools = [create_research_specialist_tool(self)]

        # Create the lead researcher agent with research specialist tools (uses main model)
        self.lead_researcher = Agent(
            model=self.model,
            system_prompt=LEAD_RESEARCHER_SYSTEM_PROMPT,
            tools=research_agent_tools,  # Give lead researcher access to research specialists
        )

    def _create_subagent_models(self):
        """Create model instances for subagents from the model pool."""
        if not self.subagent_model_pool:
            # Fallback: use main model for all subagents
            self.subagent_models = [self.model] * self.num_subagents
            return

        # Create model instances for each model ID in the pool
        self.subagent_models = []
        for model_id in self.subagent_model_pool:
            try:
                subagent_model = ModelFactory.create_model_with_id(model_id)
                self.subagent_models.append(subagent_model)
                print(f"🎭 Created subagent model: {model_id}")
            except Exception as e:
                print(f"⚠️ Failed to create subagent model {model_id}: {e}")
                # Fallback to main model for this slot
                self.subagent_models.append(self.model)

        # If no models were successfully created, fallback to main model
        if not self.subagent_models:
            print("⚠️ No subagent models created, falling back to main model")
            self.subagent_models = [self.model] * self.num_subagents

    def get_lead_researcher(self) -> Agent:
        """Get the lead researcher agent."""
        assert self.lead_researcher
        return self.lead_researcher

    def get_subagent(self, agent_id: int) -> Agent:
        """Get a specific subagent by ID."""
        return self.subagents[agent_id % len(self.subagents)]


def create_agent_manager(model: Model, num_subagents: int = 5) -> AgentManager:
    """Convenience function to create an agent manager with hybrid model support."""
    # Read subagent model pool from environment
    subagent_models_env = os.getenv("BEDROCK_SUBAGENT_MODELS")
    subagent_model_pool = []

    if subagent_models_env:
        # Parse comma-separated model IDs
        subagent_model_pool = [
            model_id.strip()
            for model_id in subagent_models_env.split(",")
            if model_id.strip()
        ]
        print(f"🎭 Using subagent model pool: {subagent_model_pool}")
    else:
        print(f"🎭 No subagent model pool specified, using main model for all agents")

    return AgentManager(model, num_subagents, subagent_model_pool)


# Agent-as-Tools Implementation
def create_research_specialist_tool(agent_manager):
    """
    Factory function that creates a research specialist tool with AgentManager.

    Args:
        agent_manager: The AgentManager instance with hybrid subagent models

    Returns:
        A research specialist tool function bound with the AgentManager
    """

    @tool
    def research_specialist(queries: List[str]) -> List[str]:
        """
        Specialized research agent that conducts concurrent web searches and analysis.
        ALWAYS processes multiple queries in parallel using diverse subagent models!

        Args:
            queries: List of research topics/questions to investigate concurrently

        Returns:
            List of comprehensive research reports corresponding to each query
        """
        tool_id = str(uuid.uuid4())
        tool_start = time.time()
        print(
            f"🔍 [{tool_id}] research_specialist tool started with {len(queries)} queries"
        )

        # Use the AgentManager's diverse subagent pool for maximum efficiency
        results = asyncio.run(
            _conduct_concurrent_research_with_agents(queries, agent_manager, tool_id)
        )

        tool_end = time.time()
        tool_time = tool_end - tool_start
        print(
            f"✅ [{tool_id}] research_specialist tool completed in {tool_time:.2f} seconds"
        )

        return results

    return research_specialist


async def _conduct_concurrent_research_with_agents(
    queries: List[str], agent_manager, tool_id: str
) -> List[str]:
    """
    Conduct research for multiple queries concurrently using AgentManager's diverse subagent pool!

    Args:
        queries: List of research topics/questions to investigate in parallel
        agent_manager: The AgentManager instance with hybrid subagent models
        tool_id: Unique identifier for this research session

    Returns:
        List of research reports corresponding to each query
    """
    concurrent_start = time.time()
    print(f"🚀 [{tool_id}] Starting concurrent research for {len(queries)} queries")

    async def research_single_async(query: str, query_index: int) -> str:
        """Async wrapper for single research task using diverse subagent models."""
        query_id = f"{tool_id}-{query_index}"
        query_start = time.time()
        print(f"  📝 [{query_id}] Starting research for: {query[:50]}...")

        # Use different subagents from the AgentManager's pool for each query
        subagent = agent_manager.get_subagent(query_index)
        subagent_model_info = getattr(subagent.model, "model_id", "unknown")
        print(f"  🎭 [{query_id}] Using subagent model: {subagent_model_info}")

        prompt = f"""What current information can you find about "{query}"? Please search for details and provide a comprehensive overview with sources."""

        try:
            response = subagent(prompt)
            # Extract text content from response
            from .orchestrator import extract_content_text

            result = "".join(map(extract_content_text, response.message["content"]))

            query_end = time.time()
            query_time = query_end - query_start
            print(
                f"  ✅ [{query_id}] Completed research for '{query[:50]}...' in {query_time:.2f} seconds"
            )

            return result
        except Exception as e:
            query_end = time.time()
            query_time = query_end - query_start
            print(
                f"  ❌ [{query_id}] Failed research for '{query[:50]}...' in {query_time:.2f} seconds: {e}"
            )
            return f"Research failed for '{query}': {str(e)}"

    # Execute all research queries concurrently using diverse subagent models
    print(f"⚡ [{tool_id}] Dispatching concurrent research tasks...")
    research_tasks = [
        research_single_async(query, i) for i, query in enumerate(queries)
    ]
    results = await asyncio.gather(*research_tasks, return_exceptions=True)

    # Convert any exceptions to error strings
    processed_results: List[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                f"Research failed for '{queries[i]}': {str(result)}"
            )
        else:
            # result should be a string at this point
            processed_results.append(str(result))

    concurrent_end = time.time()
    concurrent_time = concurrent_end - concurrent_start
    print(
        f"🎯 [{tool_id}] Concurrent research completed in {concurrent_time:.2f} seconds"
    )

    return processed_results
