"""
Research Orchestration System - Main Entry Point

A sophisticated multi-agent research orchestration system that coordinates 
lead researchers and specialized subagents for comprehensive topic investigation.
"""

import asyncio
from src.research_orchestrator import ResearchOrchestrator


def extract_content_text(c):
    """Extract text content from a content block."""
    return c.get("text", "")


async def main():
    """
    Test the research orchestration system
    """
    orchestrator = ResearchOrchestrator()
    
    test_topic = "Imaginarium Theatre Optimization Strategies in Genshin Impact"
    
    print("🚀 Research Orchestration System Test")
    print("=" * 50)
    
    try:
        results = await orchestrator.conduct_research(test_topic)
        
        print("\n✨ Research Complete!")
        print(f"📋 Final Report Summary:")
        print(f"   Main Topic: {results['main_topic']}")
        print(f"   Subtopics Researched: {results['subtopics_count']}")
        print(f"   Generated At: {results['generated_at']}")
        
        # Display master synthesis
        print(f"\n🎯 MASTER SYNTHESIS REPORT:")
        print("=" * 60)
        print(results['master_synthesis'])
        print("=" * 60)
        
        print(f"\n📚 Individual Subtopic Research:")
        for i, research in enumerate(results['subtopic_research'], 1):
            print(f"\n--- Subtopic {i}: {research['subtopic']} ---")
            print(f"Agent ID: {research['agent_id']}")
            
            # Extract text content safely from AI response
            research_summary = research['research_summary']
            if hasattr(research_summary, 'message'):
                summary_text = "".join(map(extract_content_text, research_summary.message["content"]))
            else:
                # Handle dict format
                summary_text = "".join(map(extract_content_text, research_summary.get("message", {}).get("content", [])))
            print(f"Research Summary Preview: {summary_text[:200]}...")
            # Don't print full summary since we have master synthesis now
        
    except Exception as e:
        print(f"❌ Error during research: {e}")


if __name__ == "__main__":
    asyncio.run(main())
