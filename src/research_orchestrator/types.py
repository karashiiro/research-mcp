"""
Common type definitions for the research orchestrator.

TypedDict definitions for better type safety and clarity.
"""

from typing import Any, TypedDict


class SearchResultItem(TypedDict):
    """Individual search result from web search API."""

    title: str
    url: str
    description: str
    published: str
    favicon: str


class SearchResults(TypedDict):
    """Complete search results from web search."""

    query: str
    results: list[SearchResultItem]
    total_results: int
    api_response: Any  # Raw API response data


class ResearchResults(TypedDict):
    """Complete research orchestration results."""

    main_topic: str
    subtopics_count: int
    subtopic_research: list[Any]  # Now always empty in hybrid approach
    master_synthesis: str
    summary: str
    generated_at: str
