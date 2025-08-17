"""
Master Synthesis Report Generation

Creates comprehensive master synthesis reports combining multiple subtopic research.
"""

from datetime import datetime
from typing import List, Dict, Any
from strands import Agent
from strands.types.content import ContentBlock


def extract_content_text(c: ContentBlock) -> str:
    """Extract text content from a content block."""
    return c.get("text", "")


def create_master_synthesis(main_topic: str, research_results: List[Dict[str, Any]], lead_researcher: Agent) -> str:
    """
    Create a master synthesis report combining all subtopic research
    
    Args:
        main_topic: The main research topic
        research_results: List of research results from subagents
        lead_researcher: Lead researcher agent for synthesis generation
        
    Returns:
        Master synthesis report as markdown string
    """
    try:
        # Extract all research content
        research_summaries = []
        for result in research_results:
            # Handle both dict and object response formats
            research_summary = result['research_summary']
            if hasattr(research_summary, 'message'):
                summary_text = "".join(map(extract_content_text, research_summary.message["content"]))
            else:
                # Handle dict format
                summary_text = "".join(map(extract_content_text, research_summary.get("message", {}).get("content", [])))
            
            research_summaries.append({
                "subtopic": result["subtopic"],
                "content": summary_text,
                "sources": result.get("search_results", {}).get("results", [])
            })
        
        # Create synthesis prompt with citation instructions
        synthesis_prompt = f"""Write a master synthesis report for: {main_topic}

Research data from {len(research_summaries)} subtopics:

{chr(10).join([f"SUBTOPIC: {r['subtopic']}{chr(10)}{r['content']}{chr(10)}" for r in research_summaries])}

Output format:

# Comprehensive Research Report: {main_topic}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
[Combine key findings from all subtopics - 3-4 sentences with citations]

## Key Findings by Area
{chr(10).join([f"### {r['subtopic']}{chr(10)}[Write 2-3 detailed paragraphs covering all major findings, insights, statistics, trends, and implications from this subtopic. Include specific details, metrics, and comprehensive analysis with proper citations.]{chr(10)}" for r in research_summaries])}

## Conclusion
[Overall summary - 2-3 sentences with citations]

## References
[Numbered list of all unique sources from the research data]

CITATION REQUIREMENTS:
- Include citation numbers [1], [2], [3] etc. after each factual claim
- Assign consistent numbers to sources across the entire report
- Extract all sources from the individual research reports
- Create a numbered References section with titles and URLs
- Ensure every factual statement has a proper citation

DEPTH REQUIREMENTS:
- Write comprehensive, detailed sections that preserve the rich information from individual reports
- Include specific statistics, metrics, dates, and technical details with citations
- Cover trends, developments, implications, and applications for each area
- Use natural prose paragraphs instead of bullet points or tables
- Ensure each subtopic section is thorough and in-depth (2-3 substantial paragraphs minimum)"""
        
        # Generate synthesis using lead researcher
        synthesis_response = lead_researcher(synthesis_prompt)
        
        return "".join(map(extract_content_text, synthesis_response.message["content"]))
        
    except Exception as e:
        return f"Error creating master synthesis: {e}"