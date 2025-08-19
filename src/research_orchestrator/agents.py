"""
Agent Management and System Prompts

Handles creation and management of research agents with specialized prompts.
Now implements agents-as-tools pattern for modular research orchestration.
"""

from typing import List
import asyncio
import time
import uuid
from strands import Agent, tool
from strands.models.model import Model
from .tools import get_research_tools


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
    def research_specialist(queries: List[str]) -> List[str]:
        """
        Specialized research agent that conducts concurrent web searches and analysis.
        ALWAYS processes multiple queries in parallel for maximum efficiency!

        Args:
            queries: List of research topics/questions to investigate concurrently

        Returns:
            List of comprehensive research reports corresponding to each query
        """
        tool_id = str(uuid.uuid4())
        tool_start = time.time()
        print(f"🔍 [{tool_id}] research_specialist tool started with {len(queries)} queries")
        
        # Always handle as concurrent research for maximum efficiency
        results = asyncio.run(_conduct_concurrent_research(queries, model, tool_id))
        
        tool_end = time.time()
        tool_time = tool_end - tool_start
        print(f"✅ [{tool_id}] research_specialist tool completed in {tool_time:.2f} seconds")
        
        return results

    return research_specialist


async def _conduct_concurrent_research(queries: List[str], model: Model, tool_id: str) -> List[str]:
    """
    Conduct research for multiple queries concurrently for maximum efficiency!
    
    Args:
        queries: List of research topics/questions to investigate in parallel
        model: The model instance to use
        
    Returns:
        List of research reports corresponding to each query
    """
    concurrent_start = time.time()
    print(f"🚀 [{tool_id}] Starting concurrent research for {len(queries)} queries")
    
    async def research_single_async(query: str, query_index: int) -> str:
        """Async wrapper for single research task."""
        query_id = f"{tool_id}-{query_index}"
        query_start = time.time()
        print(f"  📝 [{query_id}] Starting research for: {query[:50]}...")
        
        # Create individual research agent for this query
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
            result = "".join(map(extract_content_text, response.message["content"]))
            
            query_end = time.time()
            query_time = query_end - query_start
            print(f"  ✅ [{query_id}] Completed research for '{query[:50]}...' in {query_time:.2f} seconds")
            
            return result
        except Exception as e:
            query_end = time.time()
            query_time = query_end - query_start
            print(f"  ❌ [{query_id}] Failed research for '{query[:50]}...' in {query_time:.2f} seconds: {e}")
            return f"Research failed for '{query}': {str(e)}"
    
    # Execute all research queries concurrently
    print(f"⚡ [{tool_id}] Dispatching concurrent research tasks...")
    research_tasks = [research_single_async(query, i) for i, query in enumerate(queries)]
    results = await asyncio.gather(*research_tasks, return_exceptions=True)
    
    # Convert any exceptions to error strings
    processed_results: List[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(f"Research failed for '{queries[i]}': {str(result)}")
        else:
            # result should be a string at this point
            processed_results.append(str(result))
    
    concurrent_end = time.time()
    concurrent_time = concurrent_end - concurrent_start
    print(f"🎯 [{tool_id}] Concurrent research completed in {concurrent_time:.2f} seconds")
    
    return processed_results


def get_research_agent_tools(model: Model) -> List:
    """
    Get the list of research agent tools for the lead researcher.

    Args:
        model: The model instance to create tools with

    Returns:
        List of specialized research agent tools bound with the provided model
    """
    return [create_research_specialist_tool(model)]
