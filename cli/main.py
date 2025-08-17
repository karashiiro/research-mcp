"""
Research Orchestration System - Main Entry Point

A sophisticated multi-agent research orchestration system that coordinates
lead researchers and specialized subagents for comprehensive topic investigation.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.research_orchestrator import ResearchOrchestrator
from strands.types.content import ContentBlock


def extract_content_text(c: ContentBlock) -> str:
    """Extract text content from a content block."""
    return c.get("text", "")


async def main():
    """
    Run the research orchestration system with user-provided topic
    """
    parser = argparse.ArgumentParser(
        description="Deep Research Orchestration System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli/main.py "Machine Learning in Healthcare"
  python cli/main.py "Climate Change Impact on Agriculture"
  python cli/main.py "Imaginarium Theatre Optimization Strategies in Genshin Impact"
        """,
    )
    parser.add_argument("topic", help="Research topic to investigate comprehensively")

    args = parser.parse_args()

    orchestrator = ResearchOrchestrator()
    research_topic = args.topic

    print("🚀 Deep Research Orchestration System")
    print("=" * 50)
    print(f"📋 Research Topic: {research_topic}")
    print("=" * 50)

    try:
        results = await orchestrator.conduct_research(research_topic)

        print("\n✨ Research Complete!")
        print(f"📋 Final Report Summary:")
        print(f"   Main Topic: {results['main_topic']}")
        print(f"   Subtopics Researched: {results['subtopics_count']}")
        print(f"   Generated At: {results['generated_at']}")

        # Display master synthesis
        print(f"\n🎯 MASTER SYNTHESIS REPORT:")
        print("=" * 60)
        print(results["master_synthesis"])
        print("=" * 60)

        print(f"\n📚 Individual Subtopic Research:")
        for i, research in enumerate(results["subtopic_research"], 1):
            print(f"\n--- Subtopic {i}: {research['subtopic']} ---")
            print(f"Agent ID: {research['agent_id']}")

            # Extract text content safely from AI response
            research_summary = research["research_summary"]
            if hasattr(research_summary, "message"):
                # Handle AgentResult object format
                summary_text = "".join(
                    map(extract_content_text, research_summary.message["content"])  # type: ignore[attr-defined]
                )
            elif isinstance(research_summary, dict) and "message" in research_summary:
                # Handle dict format (AgentResponse TypedDict)
                summary_text = "".join(
                    map(extract_content_text, research_summary["message"]["content"])
                )
            else:
                # Handle other formats - fallback
                summary_text = (
                    f"Unexpected research summary format: {type(research_summary)}"
                )
            print(f"Research Summary Preview: {summary_text[:200]}...")
            # Don't print full summary since we have master synthesis now

    except Exception as e:
        print(f"❌ Error during research: {e}")


if __name__ == "__main__":
    asyncio.run(main())
