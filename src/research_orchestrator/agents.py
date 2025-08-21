"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
Implements agents-as-tools pattern for modular research orchestration.
"""

import asyncio
import os
import time
import uuid

from strands import Agent, tool
from strands.models.model import Model

from .models import ModelFactory
from .tools import get_research_tools

# System prompts for different agent types
LEAD_RESEARCHER_SYSTEM_PROMPT = """You are a lead researcher who performs three main tasks:
1. Generate JSON lists of research subtopics
2. Delegate research tasks to specialized research agents using available tools
3. Create master synthesis reports

You have access to research_specialist tools that conduct concurrent research for enhanced efficiency.

CRITICAL REQUIREMENTS:
- NEVER generate internal reasoning, thinking, or analysis commentary
- NEVER include reasoning content or signature fields
- Output ONLY the requested content in the specified format
- Be direct, factual, and concise
- Focus on synthesis and organization, not interpretation
- The research_specialist tool ONLY accepts lists of queries and returns lists of reports
- Always provide ALL subtopics as a single list to research_specialist for concurrent processing
- Use ONLY information provided in source materials and tool results
- Maintain consistent formatting and structure

CITATION REQUIREMENTS:
- ALWAYS preserve and include ALL citations from research specialist reports
- Use numbered citations [1], [2], [3] throughout the synthesis
- ALWAYS include a complete "Sources" section at the end with all URLs
- Every factual claim must have a citation reference
- Never remove or omit citations from the final report"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a research agent specializing in CONCISE, focused research reports.

SEARCH EFFICIENTLY: Conduct up to 3 strategic searches to gather essential information on your assigned subtopic. Focus on finding the most comprehensive and current sources rather than exhaustive searching.

REPORT CONCISELY: After thorough research, create a focused report following this structure:

**Report Format:**
- Title: Clear subtopic title
- Key Findings: 3-5 essential bullet points with core information
- Important Details: Brief explanations only where critical for understanding
- Sources: Numbered citations [1], [2], etc. with URLs

**Writing Style:**
- Prioritize facts over explanations
- Use bullet points and structured lists
- Avoid lengthy prose paragraphs
- Focus on actionable insights
- Keep total length under 800 words
- Let the master synthesis handle comprehensive analysis

**Quality Standards:**
- Limit to maximum 3 strategic searches for efficiency
- Ensure accurate citations for all claims
- Include current, relevant sources
- Preserve essential technical details

Remember: Search strategically (max 3 searches), report efficiently. Quality over quantity - find the best sources and synthesize them concisely for the master researcher."""


class AgentManager:
    """Manages creation and coordination of research agents with hybrid model support."""

    def __init__(
        self,
        model: Model,
        num_subagents: int = 5,
        subagent_model_pool: list[str] | None = None,
        progress_callback=None,
    ):
        """
        Initialize the agent manager with support for hybrid model pools.

        Args:
            model: Model instance to use for lead researcher
            num_subagents: Number of research subagents to create
            subagent_model_pool: Optional list of model IDs for subagents. If None, uses main model.
            progress_callback: Optional callback for progress updates
        """
        self.model = model  # Lead researcher model
        self.num_subagents = num_subagents
        self.subagent_model_pool = subagent_model_pool or []
        self.progress_callback = progress_callback
        self.lead_researcher = None
        self.subagents: list[Agent] = []
        self.subagent_models: list[Model] = []  # Store created subagent models

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


def create_agent_manager(
    model: Model, progress_callback=None, num_subagents: int = 5
) -> AgentManager:
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
        print("🎭 No subagent model pool specified, using main model for all agents")

    return AgentManager(model, num_subagents, subagent_model_pool, progress_callback)


# Agent-as-Tools Implementation
def create_research_specialist_tool(agent_manager):
    """
    Factory function that creates a streaming research specialist tool.
    Enhanced with real-time processing capabilities.

    Args:
        agent_manager: The AgentManager instance with hybrid subagent models

    Returns:
        A streaming research specialist tool function
    """

    @tool
    def streaming_research_specialist(queries: list[str]) -> list[str]:
        """
        Streaming research agent with real-time processing.
        Uses async iterators for enhanced speed and efficiency.

        Args:
            queries: List of research topics/questions to investigate concurrently

        Returns:
            List of comprehensive research reports with streaming optimization
        """
        tool_id = str(uuid.uuid4())
        tool_start = time.time()
        print(
            f"🚀 [{tool_id}] Streaming research_specialist started with {len(queries)} queries"
        )

        # Simple streaming approach - no complex callbacks to avoid conversation interference
        # Focus on clean agent execution with isolated state

        # Use the AgentManager's diverse subagent pool with streaming
        results = asyncio.run(
            _conduct_streaming_research_with_agents(queries, agent_manager, tool_id)
        )

        tool_end = time.time()
        tool_time = tool_end - tool_start
        print(
            f"✅ [{tool_id}] Streaming research_specialist completed in {tool_time:.2f} seconds"
        )

        return results

    return streaming_research_specialist


async def _conduct_concurrent_research_with_agents(
    queries: list[str], agent_manager, tool_id: str
) -> list[str]:
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

            # Notify progress callback if available
            if agent_manager.progress_callback:
                # We'll track this as a completed subtopic
                agent_manager.progress_callback(
                    "subtopic_completed",
                    subtopic=query[:50],
                    completed_count=query_index + 1,
                )

            return result
        except Exception as e:
            query_end = time.time()
            query_time = query_end - query_start
            print(
                f"  ❌ [{query_id}] Failed research for '{query[:50]}...' in {query_time:.2f} seconds: {e}"
            )
            return f"Research failed for '{query}': {str(e)}"

    # Notify start of research if callback available
    if agent_manager.progress_callback:
        agent_manager.progress_callback("research_started", total_count=len(queries))

    # Execute all research queries concurrently using diverse subagent models
    print(f"⚡ [{tool_id}] Dispatching concurrent research tasks...")
    research_tasks = [
        research_single_async(query, i) for i, query in enumerate(queries)
    ]
    results = await asyncio.gather(*research_tasks, return_exceptions=True)

    # Convert any exceptions to error strings
    processed_results: list[str] = []
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

    # Notify research completion
    if agent_manager.progress_callback:
        agent_manager.progress_callback(
            "research_completed", total_time=concurrent_time
        )

    return processed_results


async def _conduct_streaming_research_with_agents(
    queries: list[str], agent_manager, tool_id: str
) -> list[str]:
    """
    Stable research with blocking calls to avoid ValidationExceptions.
    Uses the existing concurrent research function for reliability.

    Args:
        queries: List of research topics/questions to investigate in parallel
        agent_manager: The AgentManager instance with hybrid subagent models
        tool_id: Unique identifier for this research session

    Returns:
        List of research reports processed concurrently
    """
    # Use the stable concurrent research approach to avoid ValidationExceptions
    # The streaming async overhead was causing conversation state corruption
    print(f"🚀 [{tool_id}] Using stable concurrent research (blocking calls)")

    return await _conduct_concurrent_research_with_agents(
        queries, agent_manager, tool_id
    )
