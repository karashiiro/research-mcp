"""
Research MCP Server Implementation

Provides MCP tools for comprehensive research orchestration using multi-agent systems.
"""

from mcp.server.fastmcp import FastMCP

from research_orchestrator import ResearchOrchestrator


# Create the FastMCP server instance
mcp = FastMCP("Deep Research")

# Global orchestrator instance
_orchestrator: ResearchOrchestrator | None = None


def get_orchestrator() -> ResearchOrchestrator:
    """Get or create the research orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ResearchOrchestrator()
    return _orchestrator


@mcp.tool()
async def conduct_research(topic: str) -> str:
    """
    Conduct comprehensive multi-agent research on a given topic.

    This tool orchestrates multiple specialized research agents to:
    - Break down the topic into focused subtopics
    - Conduct parallel web search and analysis
    - Generate detailed reports with proper citations
    - Create a master synthesis combining all findings

    Args:
        topic: The research topic to investigate comprehensively

    Returns:
        Complete research report with master synthesis and individual findings
    """
    orchestrator = get_orchestrator()

    try:
        # Conduct full research orchestration
        results = await orchestrator.conduct_research(topic)

        # Return the clean master synthesis report
        return results['master_synthesis']

    except Exception as e:
        return f"Error during research: {str(e)}"


if __name__ == "__main__":
    mcp.run()
