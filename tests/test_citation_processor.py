"""
Unit tests for CitationProcessor.

Tests the citation processing, URL normalization, and deduplication functionality
in isolation from the rest of the research system.
"""

from src.research_orchestrator.processing.citation_processor import (
    CitationEntry,
    CitationProcessor,
    DeduplicationResult,
)


class TestCitationProcessor:
    """Test suite for CitationProcessor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = CitationProcessor()

    def test_normalize_url_basic(self):
        """Test basic URL normalization."""
        # Test trailing slash removal
        assert (
            self.processor.normalize_url("https://example.com/")
            == "https://example.com"
        )

        # Test case normalization
        assert (
            self.processor.normalize_url("HTTPS://Example.COM/PATH")
            == "https://example.com/path"
        )

        # Test query parameter removal
        assert (
            self.processor.normalize_url("https://example.com/page?param=value")
            == "https://example.com/page"
        )

        # Test fragment removal
        assert (
            self.processor.normalize_url("https://example.com/page#section")
            == "https://example.com/page"
        )

    def test_normalize_url_edge_cases(self):
        """Test URL normalization edge cases."""
        # Test malformed URL fallback
        assert self.processor.normalize_url("not-a-url") == "not-a-url"

        # Test empty string
        assert self.processor.normalize_url("") == ""

        # Test whitespace handling
        assert (
            self.processor.normalize_url("  https://example.com/  ")
            == "https://example.com"
        )

    def test_extract_citations(self):
        """Test citation extraction from text."""
        text = """
        [1] Site One – "Article Title One" – https://example1.com/article
        [2] Site Two – "Article Title Two" – https://example2.com/page
        Some other text
        [3] Site Three – "Article Title Three" – https://example3.com/post
        """

        citations = self.processor.extract_citations(text)

        assert len(citations) == 3
        assert citations[0] == CitationEntry(
            "1", "Site One", "Article Title One", "https://example1.com/article"
        )
        assert citations[1] == CitationEntry(
            "2", "Site Two", "Article Title Two", "https://example2.com/page"
        )
        assert citations[2] == CitationEntry(
            "3", "Site Three", "Article Title Three", "https://example3.com/post"
        )

    def test_extract_sources_section(self):
        """Test extraction of Sources section from text."""
        text = """
        # Research Report

        Some research content here.

        ## Sources

        [1] Site One – "Article One" – https://example1.com
        [2] Site Two – "Article Two" – https://example2.com

        ## Additional Notes

        Some additional content.
        """

        sources_section = self.processor.extract_sources_section(text)
        assert sources_section is not None

        # The extracted section should contain both citation lines
        assert "[1] Site One" in sources_section
        assert "[2] Site Two" in sources_section
        assert "https://example1.com" in sources_section
        assert "https://example2.com" in sources_section

    def test_extract_sources_section_not_found(self):
        """Test Sources section extraction when section doesn't exist."""
        text = "# Research Report\n\nNo sources section here."

        sources_section = self.processor.extract_sources_section(text)

        assert sources_section is None

    def test_extract_urls_from_text(self):
        """Test URL extraction from text."""
        text = """
        Visit https://example1.com for more info.
        Also check http://example2.com/page and https://example3.com/article?param=value
        """

        urls = self.processor.extract_urls_from_text(text)

        expected = {
            "https://example1.com",
            "http://example2.com/page",
            "https://example3.com/article?param=value",
        }

        assert urls == expected

    def test_deduplicate_citation_urls_simple(self):
        """Test basic URL deduplication in citations."""
        synthesis = """# Research Report

This mentions source [1] and also [2].

## Sources

[1] Site Name – "Article Title" – https://example.com/page
[2] Site Name – "Same Article" – https://example.com/page/
"""

        result = self.processor.deduplicate_citation_urls(synthesis)

        assert result.deduplicated_count == 1
        assert result.final_count == 1

        # Check that the text was processed
        assert "[1]" in result.updated_text

        # Check that Sources section has only one entry
        sources_section = self.processor.extract_sources_section(result.updated_text)
        assert sources_section is not None
        citations = self.processor.extract_citations(sources_section)
        assert len(citations) == 1

    def test_deduplicate_citation_urls_no_sources(self):
        """Test deduplication when no Sources section exists."""
        synthesis = "# Research Report\n\nNo sources here."

        result = self.processor.deduplicate_citation_urls(synthesis)

        assert result.deduplicated_count == 0
        assert result.final_count == 0
        assert result.updated_text == synthesis

    def test_get_cited_urls_from_synthesis(self):
        """Test getting cited URLs from synthesis text."""
        synthesis = """# Research Report

## Sources

[1] Site One – "Article One" – https://example1.com/page
[2] Site Two – "Article Two" – https://example2.com/article/
"""

        cited_urls = self.processor.get_cited_urls_from_synthesis(synthesis)

        # URLs should be normalized
        expected = {
            "https://example1.com/page",
            "https://example2.com/article",  # trailing slash removed
        }

        assert cited_urls == expected

    def test_citation_entry_namedtuple(self):
        """Test CitationEntry namedtuple functionality."""
        citation = CitationEntry(
            "1", "Site Name", "Article Title", "https://example.com"
        )

        assert citation.old_num == "1"
        assert citation.site_name == "Site Name"
        assert citation.title == "Article Title"
        assert citation.url == "https://example.com"

    def test_deduplication_result_namedtuple(self):
        """Test DeduplicationResult namedtuple functionality."""
        result = DeduplicationResult("updated text", 2, 3)

        assert result.updated_text == "updated text"
        assert result.deduplicated_count == 2
        assert result.final_count == 3
