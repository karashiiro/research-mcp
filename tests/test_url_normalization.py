"""
Unit tests for URL normalization functionality in the research orchestrator.

Tests the normalize_url function and deduplicate_citation_urls function to ensure
proper handling of URL variations like trailing slashes, case differences,
query parameters, and fragments.
"""

from research_orchestrator.orchestrator import (
    deduplicate_citation_urls,
    normalize_url,
)


class TestUrlNormalization:
    """Test cases for the normalize_url function."""

    def test_basic_url_unchanged(self):
        """Test that a basic URL remains unchanged."""
        url = "https://example.com/path"
        assert normalize_url(url) == "https://example.com/path"

    def test_trailing_slash_removed(self):
        """Test that trailing slashes are removed."""
        url = "https://example.com/path/"
        expected = "https://example.com/path"
        assert normalize_url(url) == expected

    def test_case_normalization(self):
        """Test that URLs are converted to lowercase."""
        url = "HTTPS://EXAMPLE.COM/PATH"
        expected = "https://example.com/path"
        assert normalize_url(url) == expected

    def test_query_parameters_removed(self):
        """Test that query parameters are removed for deduplication."""
        url = "https://example.com/path?ref=google&utm_source=homepage"
        expected = "https://example.com/path"
        assert normalize_url(url) == expected

    def test_fragments_removed(self):
        """Test that fragments are removed for deduplication."""
        url = "https://example.com/path#section1"
        expected = "https://example.com/path"
        assert normalize_url(url) == expected

    def test_complex_url_normalization(self):
        """Test normalization of a complex URL with multiple components."""
        url = "HTTPS://Example.COM/x-guide/?ref=homepage&utm_source=google#strategies"
        expected = "https://example.com/x-guide"
        assert normalize_url(url) == expected

    def test_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        url = "  https://example.com/path  "
        expected = "https://example.com/path"
        assert normalize_url(url) == expected

    def test_invalid_url_fallback(self):
        """Test that invalid URLs fall back gracefully."""
        invalid_url = "not-a-valid-url"
        # Should fall back to lowercase stripped version
        assert normalize_url(invalid_url) == "not-a-valid-url"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert normalize_url("") == ""

    def test_url_variations_normalization(self):
        """Test URL variations that should be considered identical."""
        urls = [
            "https://example.com/x-guide/",
            "https://example.com/x-guide",
            "https://Example.com/x-guide",
            "https://example.com/x-guide?ref=homepage",
        ]

        expected = "https://example.com/x-guide"

        for url in urls:
            assert normalize_url(url) == expected, f"Failed for URL: {url}"


class TestCitationDeduplication:
    """Test cases for the deduplicate_citation_urls function."""

    def test_no_sources_section(self):
        """Test that text without Sources section is returned unchanged."""
        text = "This is some text without a Sources section."
        assert deduplicate_citation_urls(text) == text

    def test_no_citations_in_sources(self):
        """Test handling of Sources section with no valid citations."""
        text = """
## Some Content

This is content.

## Sources

Just some text without proper citations.
        """.strip()

        # Should return unchanged since no valid citations found
        result = deduplicate_citation_urls(text)
        assert result == text

    def test_duplicate_url_consolidation(self):
        """Test that duplicate URLs are properly consolidated."""
        text = """
This is content with citations [1] and [3] and [5].

## Sources

[1] Example Site – "Guide 1" – https://example.com/guide
[2] Different Site – "Other Guide" – https://different.example.com/guide
[3] Example Site – "Guide 2" – https://example.com/guide/
[4] Another Site – "Another Guide" – https://another.example.com/guide
[5] Example Site – "Guide 3" – https://example.com/guide?ref=homepage
        """

        result = deduplicate_citation_urls(text)

        # Should consolidate Example Site URLs to [1] and update references
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result
        assert "[4]" not in result  # Should be consolidated
        assert "[5]" not in result  # Should be consolidated

        # All Example Site references should point to [1]
        assert "citations [1] and [1] and [1]" in result

        # Sources section should have only 3 unique URLs
        sources_lines = result.split("## Sources")[1].strip().split("\n")
        actual_sources = [
            line for line in sources_lines if line.strip().startswith("[")
        ]
        assert len(actual_sources) == 3

    def test_trailing_slash_deduplication(self):
        """Test that URLs with/without trailing slashes are considered duplicates."""
        text = """
Content with [1] and [2].

## Sources

[1] Example – "Guide" – https://example.com/guide
[2] Example – "Same Guide" – https://example.com/guide/
        """

        result = deduplicate_citation_urls(text)

        # Should consolidate to single citation
        assert "[1]" in result
        assert "[2]" not in result or "[2]" not in result.split("## Sources")[1]
        assert "Content with [1] and [1]" in result

    def test_preserve_original_url_format(self):
        """Test that original URL format is preserved in the final Sources section."""
        text = """
Content [1].

## Sources

[1] Example – "Guide" – https://example.com/guide/
        """

        result = deduplicate_citation_urls(text)

        # Original URL format should be preserved
        assert "https://example.com/guide/" in result

    def test_complex_deduplication_scenario(self):
        """Test a complex scenario with multiple URL variations."""
        text = """
Research content referencing [1], [3], [5], and [7].

## Sources

[1] Wiki Site – "X Guide" – https://wiki.example.com/x-guide
[2] X Guide Site – "Guide vY.Z" – https://guides.example.com/archives/123
[3] Wiki Site – "Same Guide" – https://wiki.example.com/x-guide/
[4] Strategy Site – "Strategy Tips" – https://strategy.example.com/tips/456
[5] Wiki Site – "Guide Again" – https://wiki.example.com/x-guide?version=current
[6] Tips Site – "Guide Collection" – https://tips.example.com/x-collection
[7] Wiki Site – "Fourth Time" – https://wiki.example.com/x-guide#overview
        """

        result = deduplicate_citation_urls(text)

        # All Wiki Site URLs should be consolidated to [1]
        assert "referencing [1], [1], [1], and [1]" in result

        # Final sources should have only unique URLs
        sources_section = result.split("## Sources")[1]
        assert sources_section.count("wiki.example.com") == 1
        assert sources_section.count("guides.example.com") == 1
        assert sources_section.count("strategy.example.com") == 1
        assert sources_section.count("tips.example.com") == 1
