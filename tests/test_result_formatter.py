"""
Unit tests for ResultFormatter.

Tests result formatting, additional sources section creation, and ResearchResults
object creation in isolation from the rest of the research system.
"""

from src.research_orchestrator.processing.result_formatter import ResultFormatter
from src.research_orchestrator.processing.source_tracker import SourceTracker


class TestResultFormatter:
    """Test suite for ResultFormatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResultFormatter()
        self.source_tracker = SourceTracker()

    def test_add_additional_sources_section(self):
        """Test adding additional sources section to synthesis."""
        synthesis = "# Research Report\n\nSome content here."
        additional_sources = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com",
        ]

        result = self.formatter.add_additional_sources_section(
            synthesis, additional_sources
        )

        assert "## Additional Research Sources" in result
        assert "The following sources were also consulted" in result
        assert "- https://example1.com" in result
        assert "- https://example2.com" in result
        assert "- https://example3.com" in result
        assert "Additional sources: 3" in result

    def test_add_additional_sources_section_empty_list(self):
        """Test adding additional sources section with empty source list."""
        synthesis = "# Research Report\n\nSome content here."

        result = self.formatter.add_additional_sources_section(synthesis, [])

        # Should return unchanged synthesis
        assert result == synthesis

    def test_create_research_results(self):
        """Test creating ResearchResults object."""
        # Set up source tracker
        all_sources = [
            "https://cited1.com",
            "https://cited2.com",
            "https://additional1.com",
        ]
        self.source_tracker.add_urls(all_sources)

        # Create synthesis with some cited sources
        synthesis = """
        # Research Report

        ## Sources

        [1] Site One – "Article One" – https://cited1.com
        [2] Site Two – "Article Two" – https://cited2.com
        """

        result = self.formatter.create_research_results(
            main_topic="Test Topic",
            master_synthesis=synthesis,
            source_tracker=self.source_tracker,
            additional_context="test context",
        )

        # ResearchResults is a TypedDict, so check the dict structure
        assert result["main_topic"] == "Test Topic"
        assert result["master_synthesis"] == synthesis
        assert result["total_unique_sources"] == 3
        assert result["all_sources_used"] == sorted(all_sources)
        assert "Test Topic" in result["summary"]
        assert "test context" in result["summary"]
        assert "3 unique sources" in result["summary"]
        assert "2 directly cited" in result["summary"]
        assert "1 additional" in result["summary"]
        assert result["generated_at"]  # Should be set

    def test_create_research_results_no_additional_context(self):
        """Test creating ResearchResults without additional context."""
        self.source_tracker.add_url("https://example.com")

        synthesis = "# Research Report"

        result = self.formatter.create_research_results(
            main_topic="Test Topic",
            master_synthesis=synthesis,
            source_tracker=self.source_tracker,
        )

        assert "Test Topic" in result["summary"]
        assert "via delegation to lead researcher" in result["summary"]

    def test_process_synthesis_with_sources_deduplication(self):
        """Test processing synthesis with deduplication enabled."""
        # Set up sources
        sources = ["https://cited1.com", "https://additional1.com"]
        self.source_tracker.add_urls(sources)

        # Create synthesis with duplicate citations
        synthesis = """
        # Report

        Content with [1] and [2].

        ## Sources

        [1] Site – "Article" – https://cited1.com
        [2] Site – "Same Article" – https://cited1.com/
        """

        result = self.formatter.process_synthesis_with_sources(
            synthesis, self.source_tracker, apply_deduplication=True
        )

        # Should have deduplication applied and additional sources added
        assert "## Additional Research Sources" in result
        assert "- https://additional1.com" in result
        assert "Additional sources: 1 | Total sources consulted: 2" in result

    def test_process_synthesis_with_sources_no_deduplication(self):
        """Test processing synthesis without deduplication."""
        # Set up sources
        sources = ["https://cited1.com", "https://additional1.com"]
        self.source_tracker.add_urls(sources)

        synthesis = """
        # Report

        ## Sources

        [1] Site – "Article" – https://cited1.com
        """

        result = self.formatter.process_synthesis_with_sources(
            synthesis, self.source_tracker, apply_deduplication=False
        )

        # Should only have additional sources added, no deduplication
        assert "## Additional Research Sources" in result
        assert "- https://additional1.com" in result

    def test_process_synthesis_no_additional_sources(self):
        """Test processing synthesis when all sources are cited."""
        # Set up sources that are all cited
        sources = ["https://cited1.com"]
        self.source_tracker.add_urls(sources)

        synthesis = """# Report

## Sources

[1] Site – "Article" – https://cited1.com
"""

        result = self.formatter.process_synthesis_with_sources(
            synthesis, self.source_tracker
        )

        # Should not add additional sources section
        assert "## Additional Research Sources" not in result
        # Should be unchanged (no additional sources to add)
        assert result.strip() == synthesis.strip()

    def test_integration_with_source_tracker(self):
        """Test integration between ResultFormatter and SourceTracker."""
        # This tests the interaction between components
        sources = [
            "https://cited1.com",
            "https://cited2.com/page/",  # Will normalize to /page
            "https://additional1.com",
            "https://additional2.com",
        ]
        self.source_tracker.add_urls(sources)

        synthesis = """
        # Research Report

        Research findings [1] and [2].

        ## Sources

        [1] Site One – "Article One" – https://cited1.com
        [2] Site Two – "Article Two" – https://cited2.com/page
        """

        # Test statistics calculation
        stats = self.source_tracker.get_source_statistics(synthesis)
        assert stats["total_sources"] == 4
        assert stats["cited_sources"] == 2
        assert stats["additional_sources"] == 2

        # Test result creation
        result = self.formatter.create_research_results(
            main_topic="Integration Test",
            master_synthesis=synthesis,
            source_tracker=self.source_tracker,
        )

        assert result["total_unique_sources"] == 4
        assert "2 directly cited, 2 additional" in result["summary"]
