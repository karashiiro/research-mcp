"""
Research Orchestration Logic

Streaming architecture with real-time event processing.
Uses async iterators and framework-native optimizations for enhanced performance.
"""

import re
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse, urlunparse

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


def normalize_url(url: str) -> str:
    """
    Normalize URLs for consistent comparison using proper URL parsing.
    Handles trailing slashes, case differences, query params, and fragments.
    """
    try:
        parsed = urlparse(url.strip())

        # Normalize components
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")  # Remove trailing slash

        # Ignore query parameters and fragments for deduplication
        # (they usually don't affect the core content)

        # Reconstruct normalized URL
        normalized = urlunparse((scheme, netloc, path, "", "", ""))
        return normalized
    except Exception:
        # Fallback to original URL if parsing fails
        return url.strip().lower()


def deduplicate_citation_urls(master_synthesis: str) -> str:
    """
    Programmatically deduplicate URLs in the Sources section of master synthesis.

    This fixes the issue where the lead researcher creates multiple citation numbers
    for the same URL (e.g., [1], [5], [9] all pointing to the same URL).

    Args:
        master_synthesis: The master synthesis text with potentially duplicate URLs

    Returns:
        Fixed synthesis with deduplicated URLs and updated citation numbers
    """
    # Extract the Sources section
    sources_pattern = r"## Sources\s*\n\n(.*?)(?=\n\n##|\n\n\*\*|\Z)"
    sources_match = re.search(sources_pattern, master_synthesis, re.DOTALL)

    if not sources_match:
        return master_synthesis

    sources_section = sources_match.group(1)

    # Parse citation entries: [1] Site Name – "Title" – https://url.com (with em dashes)
    citation_pattern = r'\[(\d+)\]\s+([^–]+)\s+–\s+"([^"]+)"\s+–\s+(https?://[^\s\n]+)'
    citations = re.findall(citation_pattern, sources_section)

    if not citations:
        return master_synthesis

    # Create URL to citation mapping (deduplicate by normalized URL)
    url_to_citation = {}
    citation_counter = 1

    for old_num, site_name, title, url in citations:
        normalized_url = normalize_url(url)
        if normalized_url not in url_to_citation:
            url_to_citation[normalized_url] = {
                "new_num": citation_counter,
                "site_name": site_name.strip(),
                "title": title.strip(),
                "original_url": url,  # Keep original URL for display
                "old_nums": [old_num],
            }
            citation_counter += 1
        else:
            # Add this old citation number as an alias
            url_to_citation[normalized_url]["old_nums"].append(old_num)

    # Create mapping from old citation numbers to new ones
    old_to_new_mapping = {}
    for url_info in url_to_citation.values():
        for old_num in url_info["old_nums"]:
            old_to_new_mapping[old_num] = str(url_info["new_num"])

    # Replace citation numbers in the main text
    updated_synthesis = master_synthesis
    for old_num, new_num in old_to_new_mapping.items():
        # Replace [old_num] with [new_num] throughout the text
        updated_synthesis = re.sub(
            rf"\[{re.escape(old_num)}\]", f"[{new_num}]", updated_synthesis
        )

    # Rebuild the Sources section with deduplicated entries
    new_sources_lines = []
    for _, info in url_to_citation.items():
        new_sources_lines.append(
            f'[{info["new_num"]}] {info["site_name"]} – "{info["title"]}" – {info["original_url"]}'
        )

    new_sources_section = "\n".join(new_sources_lines)

    # Replace the old Sources section with the new one
    updated_synthesis = re.sub(
        sources_pattern,
        f"## Sources\n\n{new_sources_section}",
        updated_synthesis,
        flags=re.DOTALL,
    )

    return updated_synthesis


class ResearchOrchestrator:
    """
    Streaming research orchestrator with real-time processing.
    Uses async iterators for performance optimization.
    """

    def __init__(self, progress_callback=None):
        # Create model instance for all agents
        self.model = create_model()

        # Create agent manager with callback support
        self.agent_manager = create_agent_manager(self.model, progress_callback)

        # Set up logging
        self.research_logger = setup_logging()

        # Progress callback for real-time updates
        self.progress_callback = progress_callback

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

CRITICAL: Your final synthesis report MUST include proper citations:

- Use numbered citations [1], [2], [3] throughout the text for every factual claim
- Include a complete "Sources" section at the end listing all URLs used in numbered citations
- Preserve ALL citations from the individual research reports - never omit any sources
- Ensure every [1], [2], [3] reference in the text corresponds to a URL in the Sources section

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

            master_synthesis = "".join(
                map(extract_content_text, response.message["content"])
            )

            # Apply programmatic URL deduplication to fix citation issues
            master_synthesis = deduplicate_citation_urls(master_synthesis)
            self.research_logger.info(
                f"🔧 [{workflow_id}] Applied URL deduplication to master synthesis"
            )

            # Get source information from agent manager (set during research specialist tool execution)
            all_sources = getattr(self.agent_manager, "last_research_sources", [])
            source_count = len(all_sources)

            # Filter additional sources to exclude already cited URLs (using normalized comparison)
            # Extract all URLs from the Sources section for comparison
            cited_urls = set()
            sources_pattern = r"## Sources\s*\n\n(.*?)(?=\n\n##|\n\n\*\*|\Z)"
            sources_match = re.search(sources_pattern, master_synthesis, re.DOTALL)
            if sources_match:
                citation_pattern = r"https?://[^\s\n]+"
                cited_urls = {
                    normalize_url(url)
                    for url in re.findall(citation_pattern, sources_match.group(1))
                }

            additional_sources = [
                source
                for source in all_sources
                if normalize_url(source) not in cited_urls
            ]

            # Programmatically append Additional Research Sources section
            if additional_sources:
                additional_sources_section = "\n\n## Additional Research Sources\n\n"
                additional_sources_section += "The following sources were also consulted during research but may not be directly cited above:\n\n"

                for source in additional_sources:
                    additional_sources_section += f"- {source}\n"

                additional_sources_section += f"\nAdditional sources: {len(additional_sources)} | Total sources consulted: {source_count}"

                # Append to master synthesis
                master_synthesis += additional_sources_section

            final_report = ResearchResults(
                main_topic=main_topic,
                subtopics_count=0,
                subtopic_research=[],
                master_synthesis=master_synthesis,
                summary=f"Comprehensive research conducted on '{main_topic}' via delegation to lead researcher. Used {source_count} unique sources from research.",
                generated_at=datetime.now().isoformat(),
                total_unique_sources=source_count,
                all_sources_used=all_sources,
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
