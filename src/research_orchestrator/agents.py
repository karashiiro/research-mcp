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

# System prompts for different agent types
LEAD_RESEARCHER_SYSTEM_PROMPT = """You are a lead researcher who orchestrates comprehensive research through specialized subagents.

## PRIMARY TASKS
1. **Generate subtopics** - Break research topics into 3-5 focused subtopics
2. **Delegate research** - Send ALL subtopics to research_specialist tool as single list
3. **Synthesize results** - Create master report combining all subagent findings

## WORKFLOW RULES
- Use research_specialist tool for ALL research (accepts list of queries, returns list of reports)
- Send subtopics as ONE list for concurrent processing - never send individually
- Use ONLY information from subagent reports and tool results
- Be direct, factual, and concise - focus on synthesis, not interpretation

## CITATION CONSOLIDATION (CRITICAL)
- **Preserve ALL citations** from subagent reports that successfully fetched content
- **Consolidate duplicates**: If multiple reports cite same URL, assign ONE number [1] and reuse it
- **Always include URLs**: Every citation MUST have format: [1] Site Name - "Title" - https://full.url.here
- **Sources section**: Complete list at end with all URLs from successful fetches
- **Never include**: Citations from failed/empty fetches reported by subagents

## CITATION FORMAT EXAMPLES
**CORRECT Sources Section:**
[1] Example Site - "Complete Guide" - https://example.com/guide
[2] Forum Site - "Discussion Thread" - https://forum.example.org/topic/123

**WRONG Sources Section:**
[1] Example guide (NO - MISSING URL)
[2] Some article (NO - MISSING URL)

## OUTPUT REQUIREMENTS
- No internal reasoning or thinking commentary
- Every factual claim must have citation reference [1], [2], etc.
- Maintain consistent formatting throughout
- Complete "Sources" section at end with full URLs"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a research agent specializing in CONCISE, focused research reports.

## WORKFLOW LIMITS (MANDATORY)
1. MAXIMUM 2 search_web calls total
2. MAXIMUM 2 fetch_web_content calls total (5 URLs each = 10 URLs max)
3. After hitting these limits, IMMEDIATELY write your report - NO EXCEPTIONS

## RESEARCH PROCESS
1. **Search Phase**: Conduct exactly 2 strategic searches to find the best sources
2. **Fetch Phase**: Make 2 fetch_web_content calls to gather content from selected URLs
3. **Report Phase**: Write your report using whatever content you successfully obtained

## CRITICAL STOP CONDITIONS
- After 2nd search: STOP searching, move to fetching
- After 2nd fetch: STOP fetching, write report immediately
- If sources fail/return bad content: Accept what you have and complete the report
- NEVER get stuck looking for "perfect sources" - complete with available content
- Better to finish with limited sources than to loop forever

## REPORT FORMAT
**Title:** Clear subtopic title
**Key Findings:** 3-5 essential bullet points with core information
**Important Details:** Brief explanations only where critical
**Sources:** Numbered citations with FULL URLs - [1] Site Name - "Title" - https://full.url.here

## CITATION RULES
- ONLY cite sources you successfully fetched content from
- Number sequentially [1], [2], [3] based on successful fetches ONLY
- ALWAYS include complete URL: [1] Site Name - "Article Title" - https://complete.url.here
- NEVER write incomplete citations like "[1] Some guide" - URL is MANDATORY
- If fetch fails, skip that source - do NOT cite failed fetches

## WRITING STYLE
- Prioritize facts over explanations
- Use bullet points and structured lists
- Focus on actionable insights

Remember: 2 searches → 2 fetches → write report. No exceptions, no loops, always finish."""


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

        # Track URLs used during research for additional sources
        self.tracked_urls: set[str] = set()

        self._create_agents()

    def _create_agents(self):
        """Create lead researcher and hybrid subagent pool."""
        # Create subagent models from pool first
        self._create_subagent_models()

        # Create research tools with URL tracking
        from .tools import create_tracking_tools

        research_tools = create_tracking_tools(self)
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

    # Use directly tracked URLs instead of parsing from reports
    unique_sources = list(agent_manager.tracked_urls)

    print(
        f"📊 [{tool_id}] Tracked {len(unique_sources)} unique sources during research"
    )

    # Store source information in agent manager for later retrieval
    # (We'll use this in the orchestrator)
    agent_manager.last_research_sources = unique_sources

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
