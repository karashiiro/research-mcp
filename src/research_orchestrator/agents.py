"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
Implements agents-as-tools pattern for modular research orchestration.
"""

import asyncio
import time
import uuid

from strands import Agent, tool
from strands.models.model import Model

from .models import ModelFactory
from .settings import get_settings
from .tools import create_search_tools
from .web.content_fetcher import WebContentFetcher
from .web.search.cache import SearchCache

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

## CITATION REQUIREMENTS
- Include citations for all factual claims using format [1], [2], [3]
- Always include complete URLs in sources section: [1] Site Name - "Title" - https://full.url.here
- Only cite sources from successful subagent fetches

## OUTPUT REQUIREMENTS
- No internal reasoning or thinking commentary
- Every factual claim must have citation reference [1], [2], etc.
- Maintain consistent formatting throughout
- Complete "Sources" section at end with full URLs"""

SYNTHESIS_AGENT_SYSTEM_PROMPT = """You are a synthesis specialist who consolidates multiple research reports into a single, concise intermediate report for the lead researcher.

## PRIMARY TASK
Take multiple detailed subagent research reports and synthesize them into one streamlined intermediate report that preserves key information while reducing token overhead.

## SYNTHESIS PRINCIPLES
1. **Consolidate overlapping information** - Merge similar findings from different reports
2. **Preserve essential details** - Keep all important facts, statistics, and technical specifications
3. **Maintain all citations** - Preserve every source citation from all input reports
4. **Streamline format** - Use concise bullet points and structured lists
5. **Remove redundancy** - Eliminate duplicate information across reports

## OUTPUT FORMAT
**Research Area Overview:** Brief description of the research scope
**Consolidated Key Findings:** Essential insights from all reports (6-10 bullet points max)
**Technical Details:** Important specifications, methods, and implementation details
**Consolidated Sources:** All unique citations from input reports, renumbered sequentially

## OPTIMIZATION GUIDELINES
- Target 50% reduction in length while preserving 90% of information value
- Focus on actionable insights and concrete facts
- Eliminate verbose explanations and redundant examples
- Maintain technical accuracy and citation completeness"""

REVIEWER_AGENT_SYSTEM_PROMPT = """You are a citation review specialist focused on ensuring comprehensive source attribution in research reports.

## PRIMARY TASK
Review research reports and identify statements that need citations but currently lack them.

## REVIEW CRITERIA
1. **Factual claims** - Statistics, percentages, performance metrics, technical specifications
2. **Technical statements** - Architectural details, algorithm descriptions, model capabilities
3. **Research findings** - Experimental results, comparative analyses, benchmark scores
4. **Historical information** - Release dates, development timelines, version details
5. **Industry trends** - Market analysis, adoption patterns, future predictions

## OUTPUT FORMAT
Provide a structured review with:
- **MISSING CITATIONS IDENTIFIED:** List specific statements that need citations
- **CITATION PLACEMENT SUGGESTIONS:** Where to add [X] references in the text
- **OVERALL ASSESSMENT:** Brief summary of citation completeness

## REVIEW PRINCIPLES
- Be thorough but practical - focus on claims that genuinely need source backing
- Don't require citations for widely accepted basic concepts or definitions
- Prioritize recent statistics, performance comparisons, and technical specifications
- Flag vague statements that could be made more specific with proper sources"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a research agent specializing in CONCISE, focused research reports.

## WORKFLOW LIMITS (MANDATORY)
1. MAXIMUM 3 search_web calls total
2. MAXIMUM 3 fetch_web_content calls total (5 URLs each = 15 URLs max)
3. After hitting these limits, IMMEDIATELY write your report - NO EXCEPTIONS

## RESEARCH PROCESS
1. **Search Phase**: Conduct up to 3 strategic searches to find comprehensive sources
2. **Fetch Phase**: Make up to 3 fetch_web_content calls to gather content from selected URLs
3. **Report Phase**: Write your report using whatever content you successfully obtained

## CRITICAL STOP CONDITIONS
- After 3rd search: STOP searching, move to fetching
- After 3rd fetch: STOP fetching, write report immediately
- If sources fail/return bad content: Accept what you have and complete the report
- NEVER get stuck looking for "perfect sources" - complete with available content
- Better to finish with limited sources than to loop forever

## REPORT FORMAT
**Title:** Clear subtopic title
**Key Findings:** 4-6 essential bullet points with comprehensive information
**Important Details:** Detailed explanations with supporting evidence
**Sources:** Numbered citations with FULL URLs - [1] Site Name - "Title" - https://full.url.here

## CITATION RULES
- ONLY cite sources you successfully fetched content from
- Number sequentially [1], [2], [3] based on successful fetches ONLY
- ALWAYS include complete URL: [1] Site Name - "Article Title" - https://complete.url.here
- NEVER write incomplete citations like "[1] Some guide" - URL is MANDATORY
- If fetch fails, skip that source - do NOT cite failed fetches

## WRITING STYLE
- Provide comprehensive coverage with detailed facts and analysis
- Use bullet points and structured lists for clarity
- Include supporting evidence and context for claims
- Target thorough, in-depth coverage of the subtopic
- Focus on actionable insights with proper justification

Remember: Up to 3 searches → up to 3 fetches → write comprehensive report. No exceptions, no loops, always finish."""


class AgentManager:
    """Manages creation and coordination of research agents with hybrid model support."""

    def __init__(
        self,
        model: Model,
        num_subagents: int = 5,
        subagent_model_pool: list[str] | None = None,
        progress_callback=None,
        *,
        cache: SearchCache,
        web_fetcher: WebContentFetcher,
    ):
        """
        Initialize the agent manager with support for hybrid model pools.

        Args:
            model: Model instance to use for lead researcher
            num_subagents: Number of research subagents to create
            subagent_model_pool: Optional list of model IDs for subagents. If None, uses main model.
            progress_callback: Optional callback for progress updates
        """
        self.cache = cache
        self.web_fetcher = web_fetcher
        self.model = model  # Lead researcher model
        self.num_subagents = num_subagents
        self.subagent_model_pool = subagent_model_pool or []
        self.progress_callback = progress_callback
        self.lead_researcher = None
        self.subagents: list[Agent] = []
        self.subagent_models: list[Model] = []  # Store created subagent models
        self.reviewer_agent = None  # Citation reviewer agent
        self.synthesis_agent = None  # Report synthesis agent

        # Track URLs used during research for additional sources
        self.tracked_urls: set[str] = set()

        self._create_agents()

    def _create_agents(self):
        """Create lead researcher and hybrid subagent pool."""
        # Create subagent models from pool first
        self._create_subagent_models()

        research_tools = create_search_tools(self, self.cache, self.web_fetcher)
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

        # Create citation reviewer agent (uses main model for quality)
        self.reviewer_agent = Agent(
            model=self.model,
            system_prompt=REVIEWER_AGENT_SYSTEM_PROMPT,
        )

        # Create synthesis agent (uses main model for quality consolidation)
        self.synthesis_agent = Agent(
            model=self.model,
            system_prompt=SYNTHESIS_AGENT_SYSTEM_PROMPT,
        )

        research_agent_tools = [
            create_research_specialist_tool(self),
            create_citation_reviewer_tool(self),
        ]

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
    model: Model,
    progress_callback=None,
    num_subagents: int = 5,
    *,
    cache: SearchCache,
    web_fetcher: WebContentFetcher,
) -> AgentManager:
    """Convenience function to create an agent manager with hybrid model support."""
    settings = get_settings()
    subagent_model_pool = settings.bedrock_subagent_models_list

    if subagent_model_pool:
        print(f"🎭 Using subagent model pool: {subagent_model_pool}")
    else:
        print("🎭 No subagent model pool specified, using main model for all agents")

    return AgentManager(
        model,
        num_subagents,
        subagent_model_pool,
        progress_callback,
        cache=cache,
        web_fetcher=web_fetcher,
    )


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
    def streaming_research_specialist(queries: list[str]) -> str:
        """
        Streaming research agent with real-time processing.
        Uses async iterators for enhanced speed and efficiency.

        Args:
            queries: List of research topics/questions to investigate concurrently

        Returns:
            Synthesized research report consolidating all findings with optimized token usage
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

        # Return the synthesized report (should be a single consolidated report)
        return results[0] if results else "No research results obtained"

    return streaming_research_specialist


def create_citation_reviewer_tool(agent_manager):
    """
    Factory function that creates a citation review tool for the lead researcher.
    Reviews research reports and identifies missing citations.

    Args:
        agent_manager: The AgentManager instance containing the reviewer agent

    Returns:
        A citation reviewer tool function
    """

    @tool
    def citation_reviewer(research_report: str) -> str:
        """
        Review a research report and identify statements that need citations.

        Args:
            research_report: The complete research report text to review

        Returns:
            Detailed review highlighting missing citations and suggestions
        """
        tool_id = str(uuid.uuid4())
        tool_start = time.time()
        print(f"📝 [{tool_id}] Citation reviewer started")

        # Use the reviewer agent to analyze the report
        prompt = f"""Please review this research report and identify any statements that need citations but currently lack them:

---RESEARCH REPORT---
{research_report}
---END REPORT---

Focus on factual claims, technical specifications, performance metrics, and research findings that should be backed by sources. Provide specific suggestions for where citations should be added."""

        try:
            response = agent_manager.reviewer_agent(prompt)

            # Extract text content from response
            from .orchestrator import extract_content_text

            review_result = "".join(
                map(extract_content_text, response.message["content"])
            )

            tool_end = time.time()
            tool_time = tool_end - tool_start
            print(
                f"✅ [{tool_id}] Citation reviewer completed in {tool_time:.2f} seconds"
            )

            return review_result

        except Exception as e:
            tool_end = time.time()
            tool_time = tool_end - tool_start
            print(
                f"❌ [{tool_id}] Citation reviewer failed in {tool_time:.2f} seconds: {e}"
            )
            return f"Citation review failed: {str(e)}"

    return citation_reviewer


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

    # SYNTHESIS STEP: Consolidate all subagent reports into one intermediate report
    if len(processed_results) > 1:
        synthesis_start = time.time()
        print(
            f"🔄 [{tool_id}] Synthesizing {len(processed_results)} subagent reports..."
        )

        # Prepare synthesis prompt with all subagent reports
        reports_text = ""
        for i, report in enumerate(processed_results, 1):
            reports_text += f"\n--- SUBAGENT REPORT {i} ---\n{report}\n"

        synthesis_prompt = f"""Consolidate these {len(processed_results)} research reports into one streamlined intermediate report:

{reports_text}

Create a synthesis that preserves all key information while reducing redundancy and token overhead. Maintain all citations and technical details."""

        try:
            synthesis_response = agent_manager.synthesis_agent(synthesis_prompt)

            # Extract synthesis result
            from .orchestrator import extract_content_text

            synthesized_report = "".join(
                map(extract_content_text, synthesis_response.message["content"])
            )

            synthesis_end = time.time()
            synthesis_time = synthesis_end - synthesis_start
            print(f"🎯 [{tool_id}] Synthesis completed in {synthesis_time:.2f} seconds")

            # Return the single synthesized report instead of multiple reports
            return [synthesized_report]

        except Exception as e:
            synthesis_end = time.time()
            synthesis_time = synthesis_end - synthesis_start
            print(
                f"❌ [{tool_id}] Synthesis failed in {synthesis_time:.2f} seconds: {e}"
            )
            print(f"⚠️ [{tool_id}] Falling back to original reports")
            # Fall back to original reports if synthesis fails

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
