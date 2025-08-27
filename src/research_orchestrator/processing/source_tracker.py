"""
Source tracking and management.

Handles tracking URLs used during research, filtering additional sources,
and managing source collections. Designed for easy testing and clear separation of concerns.
"""

from .citation_processor import CitationProcessor


class SourceTracker:
    """Tracks and manages research sources throughout the research process."""

    def __init__(self):
        """Initialize the source tracker."""
        self.citation_processor = CitationProcessor()
        self.tracked_urls: set[str] = set()

    def add_url(self, url: str) -> None:
        """
        Add a URL to the tracked sources.

        Args:
            url: URL to add to tracking
        """
        self.tracked_urls.add(url)

    def add_urls(self, urls: list[str]) -> None:
        """
        Add multiple URLs to the tracked sources.

        Args:
            urls: List of URLs to add to tracking
        """
        self.tracked_urls.update(urls)

    def get_all_sources(self) -> list[str]:
        """
        Get all tracked sources as a sorted list.

        Returns:
            Sorted list of all tracked URLs
        """
        return sorted(self.tracked_urls)

    def get_additional_sources(self, synthesis_text: str) -> list[str]:
        """
        Get sources that were tracked but not directly cited in the synthesis.

        Args:
            synthesis_text: The synthesis text with Sources section

        Returns:
            List of additional (non-cited) sources
        """
        # Get URLs that are cited in the synthesis
        cited_urls = self.citation_processor.get_cited_urls_from_synthesis(
            synthesis_text
        )

        # Filter tracked URLs to exclude already cited ones (using normalized comparison)
        additional_sources = [
            source
            for source in self.get_all_sources()
            if self.citation_processor.normalize_url(source) not in cited_urls
        ]

        return additional_sources

    def get_source_statistics(self, synthesis_text: str) -> dict:
        """
        Get statistics about source usage.

        Args:
            synthesis_text: The synthesis text with Sources section

        Returns:
            Dictionary with source statistics
        """
        all_sources = self.get_all_sources()
        additional_sources = self.get_additional_sources(synthesis_text)
        cited_sources = len(all_sources) - len(additional_sources)

        return {
            "total_sources": len(all_sources),
            "cited_sources": cited_sources,
            "additional_sources": len(additional_sources),
            "citation_rate": cited_sources / len(all_sources) if all_sources else 0.0,
        }

    def clear(self) -> None:
        """Clear all tracked sources."""
        self.tracked_urls.clear()

    def __len__(self) -> int:
        """Return the number of tracked sources."""
        return len(self.tracked_urls)

    def __contains__(self, url: str) -> bool:
        """Check if a URL is being tracked."""
        return url in self.tracked_urls
