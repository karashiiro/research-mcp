"""
Unit tests for SourceTracker.

Tests source tracking, additional source filtering, and statistics functionality
in isolation from the rest of the research system.
"""

from src.research_orchestrator.processing.source_tracker import SourceTracker


class TestSourceTracker:
    """Test suite for SourceTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = SourceTracker()

    def test_add_url(self):
        """Test adding a single URL."""
        self.tracker.add_url("https://example.com")

        assert len(self.tracker) == 1
        assert "https://example.com" in self.tracker
        assert self.tracker.get_all_sources() == ["https://example.com"]

    def test_add_urls_multiple(self):
        """Test adding multiple URLs."""
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        self.tracker.add_urls(urls)

        assert len(self.tracker) == 3
        for url in urls:
            assert url in self.tracker

    def test_add_urls_duplicates(self):
        """Test that duplicate URLs are not added twice."""
        self.tracker.add_url("https://example.com")
        self.tracker.add_url("https://example.com")  # Duplicate

        assert len(self.tracker) == 1

    def test_get_all_sources_sorted(self):
        """Test that get_all_sources returns sorted list."""
        urls = ["https://zebra.com", "https://apple.com", "https://banana.com"]

        self.tracker.add_urls(urls)
        sources = self.tracker.get_all_sources()

        assert sources == sorted(urls)

    def test_get_additional_sources(self):
        """Test filtering additional sources from synthesis."""
        # Add tracked URLs
        all_sources = [
            "https://cited1.com",
            "https://cited2.com",
            "https://additional1.com",
            "https://additional2.com",
        ]
        self.tracker.add_urls(all_sources)

        # Create synthesis with some of these URLs cited
        synthesis = """
        # Research Report

        Some research content [1] and [2].

        ## Sources

        [1] Site One – "Article One" – https://cited1.com
        [2] Site Two – "Article Two" – https://cited2.com/
        """

        additional = self.tracker.get_additional_sources(synthesis)

        # Should return the sources that aren't cited
        expected = ["https://additional1.com", "https://additional2.com"]
        assert set(additional) == set(expected)

    def test_get_additional_sources_no_synthesis_sources(self):
        """Test additional sources when synthesis has no Sources section."""
        self.tracker.add_urls(["https://example1.com", "https://example2.com"])

        synthesis = "# Research Report\n\nNo sources section."
        additional = self.tracker.get_additional_sources(synthesis)

        # All sources should be considered additional
        assert set(additional) == {"https://example1.com", "https://example2.com"}

    def test_get_source_statistics(self):
        """Test source usage statistics."""
        # Add sources
        all_sources = [
            "https://cited1.com",
            "https://cited2.com",
            "https://additional1.com",
            "https://additional2.com",
        ]
        self.tracker.add_urls(all_sources)

        # Create synthesis with 2 cited sources
        synthesis = """
        ## Sources

        [1] Site One – "Article One" – https://cited1.com
        [2] Site Two – "Article Two" – https://cited2.com
        """

        stats = self.tracker.get_source_statistics(synthesis)

        assert stats["total_sources"] == 4
        assert stats["cited_sources"] == 2
        assert stats["additional_sources"] == 2
        assert stats["citation_rate"] == 0.5  # 2/4

    def test_get_source_statistics_empty_tracker(self):
        """Test statistics with empty tracker."""
        synthesis = "# Empty report"
        stats = self.tracker.get_source_statistics(synthesis)

        assert stats["total_sources"] == 0
        assert stats["cited_sources"] == 0
        assert stats["additional_sources"] == 0
        assert stats["citation_rate"] == 0.0

    def test_clear(self):
        """Test clearing all sources."""
        self.tracker.add_urls(["https://example1.com", "https://example2.com"])
        assert len(self.tracker) == 2

        self.tracker.clear()
        assert len(self.tracker) == 0
        assert self.tracker.get_all_sources() == []

    def test_contains_operator(self):
        """Test the 'in' operator functionality."""
        self.tracker.add_url("https://example.com")

        assert "https://example.com" in self.tracker
        assert "https://other.com" not in self.tracker

    def test_len_operator(self):
        """Test the len() functionality."""
        assert len(self.tracker) == 0

        self.tracker.add_url("https://example.com")
        assert len(self.tracker) == 1

        self.tracker.add_urls(["https://example2.com", "https://example3.com"])
        assert len(self.tracker) == 3

    def test_normalized_url_comparison(self):
        """Test that URL normalization works correctly for filtering."""
        # Add sources with different URL formats
        self.tracker.add_urls(["https://example.com/page", "https://other.com/article"])

        # Create synthesis with normalized versions of URLs
        synthesis = """
        ## Sources

        [1] Site – "Article" – https://example.com/page/
        """

        additional = self.tracker.get_additional_sources(synthesis)

        # Only the non-matching URL should be additional
        # (https://example.com/page should match https://example.com/page/ after normalization)
        assert additional == ["https://other.com/article"]
