"""
Research Orchestration Logic

Streaming architecture with real-time event processing.
Uses async iterators and framework-native optimizations for enhanced performance.
"""

import time
import uuid

from strands.types.content import ContentBlock

from .agents import create_agent_manager
from .logger import setup_logging
from .models import create_model
from .processing import CitationProcessor, ResultFormatter, SourceTracker
from .types import ResearchResults
from .web.content_fetcher import WebContentFetcher
from .web.search.cache import SearchCache


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
    Streaming research orchestrator with real-time processing.
    Uses async iterators for performance optimization.
    """

    def __init__(
        self,
        progress_callback=None,
        *,
        cache: SearchCache,
        web_fetcher: WebContentFetcher,
    ):
        # Create model instance for all agents
        self.model = create_model()

        # Create agent manager with callback support
        self.agent_manager = create_agent_manager(
            self.model, progress_callback, cache=cache, web_fetcher=web_fetcher
        )

        # Set up logging
        self.research_logger = setup_logging()

        # Progress callback for real-time updates
        self.progress_callback = progress_callback

        # Initialize processing components
        self.citation_processor = CitationProcessor()
        self.result_formatter = ResultFormatter()
        self.source_tracker = SourceTracker()

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
3. Review initial findings to identify areas for deeper investigation
4. Consider using research_specialist tool again with 1-2 follow-up topics to explore interesting areas in greater depth
5. Create a comprehensive master synthesis report combining ALL findings (initial + follow-up)
6. Include proper citations, structure, and formatting

FOLLOW-UP RESEARCH CONSIDERATIONS:
- After reviewing initial research, consider whether additional depth would enhance the final report
- Good candidates for follow-up: advanced techniques, recent developments, practical implementation, emerging trends, detailed mechanisms
- Follow-up topics should build upon interesting findings from the initial research
- Use your judgment about whether the topic would benefit from additional investigation

CRITICAL: Your final synthesis report MUST include proper citations:

- Use numbered citations [1], [2], [3] throughout the text for every factual claim
- Include a complete "Sources" section at the end listing all URLs used in numbered citations
- Preserve ALL citations from ALL research rounds (initial + follow-up) - never omit any sources
- Ensure every [1], [2], [3] reference in the text corresponds to a URL in the Sources section

CITATION REVIEW WORKFLOW:
1. After completing your master synthesis report, use the citation_reviewer tool to check for missing citations
2. The reviewer will identify statements that need citations but currently lack them
3. If significant issues are found, consider making improvements to the report before finalizing

Return ONLY the final master synthesis report as your complete response. No JSON, no metadata, just the comprehensive research report that synthesizes all your findings with complete citations and source transparency."""

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

            raw_synthesis = "".join(
                map(extract_content_text, response.message["content"])
            )

            # Initialize source tracker with sources from agent manager
            all_sources = self.agent_manager.last_research_sources
            self.source_tracker.add_urls(all_sources)

            # Process synthesis with citation deduplication and additional sources
            processed_synthesis = self.result_formatter.process_synthesis_with_sources(
                raw_synthesis, self.source_tracker, apply_deduplication=True
            )

            self.research_logger.info(
                f"🔧 [{workflow_id}] Applied URL deduplication and added additional sources"
            )

            # Create final report using result formatter
            final_report = self.result_formatter.create_research_results(
                main_topic=main_topic,
                master_synthesis=processed_synthesis,
                source_tracker=self.source_tracker,
                additional_context="via delegation to lead researcher",
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
        Research orchestration with stable blocking calls to avoid ValidationExceptions.
        """
        self.research_logger.info(
            f"🚀 Starting research orchestration for: {main_topic}"
        )
        self.research_logger.info("⚡ Using stable architecture with hybrid model pool")

        # Use stable workflow to avoid ValidationExceptions
        final_report = await self.complete_research_workflow(main_topic)

        self.research_logger.info("✨ Research workflow completed")
        return final_report
