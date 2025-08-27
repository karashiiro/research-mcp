"""
Citation processing and URL management.

Handles URL normalization, citation deduplication, and citation extraction
from research reports. Designed to be highly testable in isolation.
"""

import re
from typing import Any, NamedTuple
from urllib.parse import urlparse, urlunparse


class CitationEntry(NamedTuple):
    """Represents a parsed citation entry."""

    old_num: str
    site_name: str
    title: str
    url: str


class DeduplicationResult(NamedTuple):
    """Result of citation deduplication process."""

    updated_text: str
    deduplicated_count: int
    final_count: int


class CitationProcessor:
    """Processes citations and manages URL deduplication in research reports."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URLs for consistent comparison using proper URL parsing.
        Handles trailing slashes, case differences, query params, and fragments.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL string
        """
        try:
            parsed = urlparse(url.strip())

            # Normalize components
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip(
                "/"
            ).lower()  # Remove trailing slash and lowercase

            # Ignore query parameters and fragments for deduplication
            # (they usually don't affect the core content)

            # Reconstruct normalized URL
            normalized = urlunparse((scheme, netloc, path, "", "", ""))
            return normalized
        except Exception:
            # Fallback to original URL if parsing fails
            return url.strip().lower()

    @staticmethod
    def extract_citations(text: str) -> list[CitationEntry]:
        """
        Extract citation entries from a text.

        Args:
            text: Text containing citations

        Returns:
            List of CitationEntry objects
        """
        # Parse citation entries: [1] Site Name – "Title" – https://url.com (with em dashes)
        citation_pattern = (
            r'\[(\d+)\]\s+([^–]+)\s+–\s+"([^"]+)"\s+–\s+(https?://[^\s\n]+)'
        )
        citations = re.findall(citation_pattern, text)

        return [
            CitationEntry(
                old_num=old_num,
                site_name=site_name.strip(),
                title=title.strip(),
                url=url,
            )
            for old_num, site_name, title, url in citations
        ]

    @staticmethod
    def extract_sources_section(text: str) -> str | None:
        """
        Extract the Sources section from a text.

        Args:
            text: Text containing a Sources section

        Returns:
            Sources section content or None if not found
        """
        sources_pattern = (
            r"##\s*Sources\s*\n\s*\n(.*?)(?=\n\s*\n\s*##|\n\s*\n\s*\*\*|\Z)"
        )
        sources_match = re.search(sources_pattern, text, re.DOTALL)

        return sources_match.group(1).strip() if sources_match else None

    @staticmethod
    def extract_urls_from_text(text: str) -> set[str]:
        """
        Extract all URLs from a text.

        Args:
            text: Text containing URLs

        Returns:
            Set of URLs found in the text
        """
        url_pattern = r"https?://[^\s\n]+"
        return set(re.findall(url_pattern, text))

    def deduplicate_citation_urls(self, master_synthesis: str) -> DeduplicationResult:
        """
        Programmatically deduplicate URLs in the Sources section of master synthesis.

        This fixes the issue where the lead researcher creates multiple citation numbers
        for the same URL (e.g., [1], [5], [9] all pointing to the same URL).

        Args:
            master_synthesis: The master synthesis text with potentially duplicate URLs

        Returns:
            DeduplicationResult with updated text and statistics
        """
        # Extract the Sources section
        sources_section = self.extract_sources_section(master_synthesis)
        if not sources_section:
            return DeduplicationResult(
                updated_text=master_synthesis, deduplicated_count=0, final_count=0
            )

        # Extract citations
        citations = self.extract_citations(sources_section)
        if not citations:
            return DeduplicationResult(
                updated_text=master_synthesis, deduplicated_count=0, final_count=0
            )

        original_count = len(citations)

        # Create URL to citation mapping (deduplicate by normalized URL)
        url_to_citation: dict[str, dict[str, Any]] = {}
        citation_counter = 1

        for citation in citations:
            normalized_url = self.normalize_url(citation.url)
            if normalized_url not in url_to_citation:
                url_to_citation[normalized_url] = {
                    "new_num": citation_counter,
                    "site_name": citation.site_name,
                    "title": citation.title,
                    "original_url": citation.url,  # Keep original URL for display
                    "old_nums": [citation.old_num],
                }
                citation_counter += 1
            else:
                # Add this old citation number as an alias
                url_to_citation[normalized_url]["old_nums"].append(citation.old_num)

        final_count = len(url_to_citation)

        # Create mapping from old citation numbers to new ones
        old_to_new_mapping: dict[str, str] = {}
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
        sources_pattern = (
            r"##\s*Sources\s*\n\s*\n(.*?)(?=\n\s*\n\s*##|\n\s*\n\s*\*\*|\Z)"
        )
        updated_synthesis = re.sub(
            sources_pattern,
            f"## Sources\n\n{new_sources_section}",
            updated_synthesis,
            flags=re.DOTALL,
        )

        deduplicated_count = original_count - final_count

        return DeduplicationResult(
            updated_text=updated_synthesis,
            deduplicated_count=deduplicated_count,
            final_count=final_count,
        )

    def get_cited_urls_from_synthesis(self, synthesis_text: str) -> set[str]:
        """
        Get all URLs that are cited in the synthesis Sources section.

        Args:
            synthesis_text: The synthesis text containing Sources section

        Returns:
            Set of normalized URLs that are cited
        """
        sources_section = self.extract_sources_section(synthesis_text)
        if not sources_section:
            return set()

        urls = self.extract_urls_from_text(sources_section)
        return {self.normalize_url(url) for url in urls}
