"""
Research MCP Server Implementation

Provides MCP tools for comprehensive research orchestration using multi-agent systems.
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Redirect print statements to stderr to avoid breaking MCP JSON protocol
import builtins

original_print = builtins.print


def mcp_safe_print(*args, **kwargs):
    kwargs["file"] = kwargs.get("file", sys.stderr)
    original_print(*args, **kwargs)


builtins.print = mcp_safe_print

from research_orchestrator import ResearchOrchestrator  # type: ignore  # noqa: E402

# Create the FastMCP server instance
mcp = FastMCP("Deep Research")


@mcp.tool()
async def conduct_research(topic: str) -> str:
    """
    <tool_description>
    Conduct comprehensive multi-agent research on a given topic.

    This tool orchestrates multiple specialized research agents to:
    - Break down the topic into focused subtopics
    - Conduct parallel web search and analysis
    - Generate detailed reports with proper citations
    - Create a master synthesis combining all findings
    </tool_description>

    <tool_usage_guidelines>
    Use this tool for comprehensive guides, mastery-level explanations, or when someone asks for 'research' on complex topics!
    Perfect for any subject where you'd need multiple sources to give a truly complete answer - whether it's academic research, hobby deep-dives, professional strategies, or detailed how-to guides.
    If they want to go from beginner to expert understanding, or if the topic has interconnected systems that need thorough explanation, this is your tool!

    Also use this tool for ANY comprehensive guides, strategy guides, or 'tell me everything about X' requests, even for topics like gaming, hobbies, or specialized interests.
    Gaming strategies, meta analysis, or evolving systems especially benefit from current research.

    DO NOT use this tool for lifestyle advice, creative writing, or other opinion-based responses.

    Unless you have already found relevant research or sources to cite FROM OTHER TOOLS, this tool is effectively MANDATORY to use at least once per topic.
    It ensures you provide a well-rounded, credible, and thoroughly researched response that users can trust and reference.

    However, this tool is also expensive, so you MUST ASK the user for confirmation before running it.
    </tool_usage_guidelines>

    <output_formatting_requirements>
    When presenting research results, follow these guidelines based on your capabilities:

    MAIN RESPONSE FORMATTING:
    - Even when creating artifacts, the main conversational response should follow prose formatting guidelines.
    - Avoid bullet points, numbered lists, or excessive formatting in explanatory text.
    - Use natural language flow: "The key elements include: A, B, and C" rather than bulleted lists.

    CITATION REQUIREMENTS:
    - Use linked inline reference numbers in Markdown format [[1](link)], [[2](link)], etc. and ensure the references list from the research report is included at the end of your response
    - ALWAYS preserve source attribution regardless of citation method available

    CRITICAL: CITATION REQUIREMENTS (HIGH PRIORITY)
    - MUST cite all factual claims from research
    - Use factual claim for every specific detail, strategy, or data point
    - This is mandatory, not optional - factual claims without citations undermine research credibility
    - No exceptions - if you reference research findings, cite them immediately
    - Use specific index numbers from the research report
    - Failure to cite = academic integrity violation

    CONTENT FORMATTING:
    - IF you have artifact creation capabilities AND the research produces substantial structured content (guides, reports, reference materials): Create an appropriate artifact containing the complete information
    - IF you do NOT have artifact capabilities: Format the content clearly in your response using proper markdown structure with headers, sections, and lists
    - ALWAYS prioritize making the information easily scannable and referenceable

    FALLBACK BEHAVIOR:
    - When specific formatting tools are unavailable, compensate with clear structure, proper headings, and explicit source attribution
    - Ensure information remains credible and verifiable regardless of presentation format
    - Include complete reference list at the end of response when citation markup is unavailable
    </output_formatting_requirements>

    <tool_result_guidelines>
    Upon receiving a result, format it in a manner that suits the user's original request.
    Structure your response to maximize credibility and usability:

    1. DETERMINE YOUR CAPABILITIES: Check what environment you're in and what formatting tools are available
    2. FORMAT APPROPRIATELY: Use artifacts for substantial content if available and appropriate, otherwise use clear Markdown structure
    3. CITE SOURCES PROPERLY: Use numbered references with the number linked as a Markdown link [[1](link)], [[2](link)], etc.
    4. MAINTAIN CREDIBILITY: Always preserve source attribution and enable verification regardless of formatting method or environment

    The goal is to provide comprehensive, well-structured, and properly attributed research results that users can trust and reference, adapted to your specific capabilities.
    </tool_result_guidelines>

    Args:
        topic: The research topic to investigate comprehensively. Format this as a single,
        focused question or statement (e.g., "Impact of AI on Healthcare"). The research
        agent will break it down into subtopics and conduct detailed research.

    Returns:
        Complete research report with master synthesis and individual findings
    """
    orchestrator = ResearchOrchestrator()

    try:
        # Conduct full research orchestration
        results = await orchestrator.conduct_research(topic)

        # Return the clean master synthesis report
        return results["master_synthesis"]

    except Exception as e:
        return f"Error during research: {str(e)}"


if __name__ == "__main__":
    mcp.run()
