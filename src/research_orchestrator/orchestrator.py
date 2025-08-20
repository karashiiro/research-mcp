"""
Research Orchestration Logic

Simplified architecture with complete delegation to lead researcher.
The lead researcher handles subtopic generation, concurrent research, and synthesis.
The research_specialist tool enforces concurrency by only accepting lists of queries.
"""

import time
import uuid
from datetime import datetime
from strands.types.content import ContentBlock

from .agents import create_agent_manager
from .config import setup_logging
from .models import create_model
from .types import ResearchResults


def extract_content_text(c: ContentBlock) -> str:
    """Extract text content from a content block, handling reasoning content."""
    # Handle direct text content
    if "text" in c:
        return c["text"]
    # Handle reasoning content format
    elif "reasoningContent" in c:
        reasoning = c["reasoningContent"]
        if "reasoningText" in reasoning and "text" in reasoning["reasoningText"]:
            return reasoning["reasoningText"]["text"]
    return ""


class ResearchOrchestrator:
    """
    Research orchestrator that delegates complete research workflows to lead researcher.
    """

    def __init__(self):
        # Create model instance for all agents
        self.model = create_model()

        # Create agent manager
        self.agent_manager = create_agent_manager(self.model)

        # Set up logging
        self.research_logger = setup_logging()

    async def complete_research_workflow(self, main_topic: str) -> ResearchResults:
        """
        Delegates the complete research workflow to the lead researcher.
        """
        workflow_id = str(uuid.uuid4())
        workflow_start = time.time()
        self.research_logger.info(
            f"🕐 [{workflow_id}] Starting complete research workflow for: {main_topic}"
        )

        lead_researcher = self.agent_manager.get_lead_researcher()

        prompt = f"""As lead researcher, conduct a complete research workflow for the topic: "{main_topic}"

COMPLETE WORKFLOW:
1. Generate 2-5 focused subtopics for comprehensive coverage
2. Use research_specialist tool with ALL subtopics to get concurrent research reports  
3. Create a comprehensive master synthesis report combining all findings
4. Include proper citations, structure, and formatting

Return ONLY the final master synthesis report as your complete response. No JSON, no metadata, just the comprehensive research report that synthesizes all your findings."""

        try:
            delegation_start = time.time()
            self.research_logger.info(
                f"⏱️ [{workflow_id}] Delegating to lead researcher..."
            )

            response = lead_researcher(prompt)

            delegation_end = time.time()
            delegation_time = delegation_end - delegation_start
            self.research_logger.info(
                f"✅ [{workflow_id}] Lead researcher completed in {delegation_time:.2f} seconds"
            )

            processing_start = time.time()
            self.research_logger.info(f"🔄 [{workflow_id}] Processing response...")

            master_synthesis = "".join(
                map(extract_content_text, response.message["content"])
            )

            final_report = ResearchResults(
                main_topic=main_topic,
                subtopics_count=0,
                subtopic_research=[],
                master_synthesis=master_synthesis,
                summary=f"Comprehensive research conducted on '{main_topic}' via delegation to lead researcher.",
                generated_at=datetime.now().isoformat(),
            )

            processing_end = time.time()
            processing_time = processing_end - processing_start
            workflow_end = time.time()
            total_time = workflow_end - workflow_start

            self.research_logger.info(
                f"⚡ [{workflow_id}] Response processing completed in {processing_time:.2f} seconds"
            )
            self.research_logger.info(
                f"🎯 [{workflow_id}] Complete research workflow finished for '{main_topic}' in {total_time:.2f} seconds total"
            )

            return final_report

        except Exception as e:
            workflow_end = time.time()
            total_time = workflow_end - workflow_start
            self.research_logger.error(
                f"❌ [{workflow_id}] Complete workflow delegation failed for '{main_topic}' after {total_time:.2f} seconds: {e}"
            )
            raise RuntimeError(
                f"Research workflow failed for topic '{main_topic}': {str(e)}"
            ) from e

    async def conduct_research(self, main_topic: str) -> ResearchResults:
        """
        Orchestrate the complete research process by delegating to lead researcher.
        """
        self.research_logger.info(f"Starting research orchestration for: {main_topic}")
        self.research_logger.info("Delegating research workflow to lead researcher")

        final_report = await self.complete_research_workflow(main_topic)

        self.research_logger.info("Research workflow completed")
        return final_report
