"""
Result formatting and output processing.

Handles formatting research results, building additional sources sections,
and creating the final ResearchResults objects. Focused on output formatting concerns.
"""

from datetime import datetime

from ..types import ResearchResults
from .citation_processor import CitationProcessor
from .source_tracker import SourceTracker


class ResultFormatter:
    """Formats research results and handles output processing."""

    def __init__(self):
        """Initialize the result formatter."""
        self.citation_processor = CitationProcessor()

    def add_additional_sources_section(
        self, synthesis_text: str, additional_sources: list[str]
    ) -> str:
        """
        Add an Additional Research Sources section to the synthesis text.

        Args:
            synthesis_text: The main synthesis text
            additional_sources: List of additional source URLs

        Returns:
            Synthesis text with additional sources section appended
        """
        if not additional_sources:
            return synthesis_text

        additional_sources_section = "\n\n## Additional Research Sources\n\n"
        additional_sources_section += (
            "The following sources were also consulted during research "
            "but may not be directly cited above:\n\n"
        )

        for source in additional_sources:
            additional_sources_section += f"- {source}\n"

        total_sources = len(additional_sources)
        additional_sources_section += f"\nAdditional sources: {total_sources}"

        return synthesis_text + additional_sources_section

    def create_research_results(
        self,
        main_topic: str,
        master_synthesis: str,
        source_tracker: SourceTracker,
        additional_context: str = "",
    ) -> ResearchResults:
        """
        Create a complete ResearchResults object from the processed components.

        Args:
            main_topic: The main research topic
            master_synthesis: The processed master synthesis text
            source_tracker: SourceTracker instance with all tracked sources
            additional_context: Additional context for the summary

        Returns:
            Complete ResearchResults object
        """
        all_sources = source_tracker.get_all_sources()
        source_stats = source_tracker.get_source_statistics(master_synthesis)

        # Create summary with statistics
        summary_parts = [
            f"Comprehensive research conducted on '{main_topic}' via delegation to lead researcher."
        ]

        if additional_context:
            summary_parts.append(additional_context)

        summary_parts.append(
            f"Used {source_stats['total_sources']} unique sources from research "
            f"({source_stats['cited_sources']} directly cited, "
            f"{source_stats['additional_sources']} additional)."
        )

        summary = " ".join(summary_parts)

        return ResearchResults(
            main_topic=main_topic,
            subtopics_count=0,  # Legacy field - could be calculated if needed
            subtopic_research=[],  # Legacy field - could be populated if needed
            master_synthesis=master_synthesis,
            summary=summary,
            generated_at=datetime.now().isoformat(),
            total_unique_sources=source_stats["total_sources"],
            all_sources_used=all_sources,
        )

    def process_synthesis_with_sources(
        self,
        synthesis_text: str,
        source_tracker: SourceTracker,
        apply_deduplication: bool = True,
    ) -> str:
        """
        Process synthesis text with citation deduplication and additional sources.

        Args:
            synthesis_text: Raw synthesis text from research
            source_tracker: SourceTracker with all research sources
            apply_deduplication: Whether to apply URL deduplication

        Returns:
            Processed synthesis text with deduplication and additional sources
        """
        # Apply citation deduplication if requested
        if apply_deduplication:
            dedup_result = self.citation_processor.deduplicate_citation_urls(
                synthesis_text
            )
            processed_synthesis = dedup_result.updated_text
        else:
            processed_synthesis = synthesis_text

        # Add additional sources section
        additional_sources = source_tracker.get_additional_sources(processed_synthesis)
        if additional_sources:
            total_sources = len(source_tracker.get_all_sources())

            additional_sources_section = "\n\n## Additional Research Sources\n\n"
            additional_sources_section += (
                "The following sources were also consulted during research "
                "but may not be directly cited above:\n\n"
            )

            for source in additional_sources:
                additional_sources_section += f"- {source}\n"

            additional_sources_section += (
                f"\nAdditional sources: {len(additional_sources)} | "
                f"Total sources consulted: {total_sources}"
            )

            processed_synthesis += additional_sources_section

        return processed_synthesis
