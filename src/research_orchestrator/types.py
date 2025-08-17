"""
Common type definitions for the research orchestrator.

TypedDict definitions for better type safety and clarity.
"""

from typing import TypedDict, List, Any, Optional
from strands.types.content import ContentBlock


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
    results: List[SearchResultItem]
    total_results: int
    api_response: Any  # Raw API response data


class CompatSearchResultItem(TypedDict):
    """Compatible search result format for orchestrator (legacy format)."""

    title: str
    snippet: str  # Note: uses 'snippet' instead of 'description'
    url: str


class CompatSearchResults(TypedDict):
    """Compatible search results format for orchestrator."""

    query: str
    results: List[CompatSearchResultItem]
    error: Optional[str]


class AgentMessage(TypedDict):
    """Agent response message structure."""

    content: List[ContentBlock]


class AgentResponse(TypedDict):
    """Complete agent response structure."""

    message: AgentMessage


class SubtopicResearch(TypedDict):
    """Research results for a single subtopic."""

    subtopic: str
    agent_id: int
    search_results: CompatSearchResults
    research_summary: AgentResponse


class ResearchResults(TypedDict):
    """Complete research orchestration results."""

    main_topic: str
    subtopics_count: int
    subtopic_research: List[SubtopicResearch]
    master_synthesis: str
    summary: str
    generated_at: str


class CacheMetadata(TypedDict):
    """Cache metadata structure."""

    version: str
    created_at: str
    last_accessed: str
    total_entries: int


class CacheEntry(TypedDict):
    """Individual cache entry structure."""

    query: str
    count: int
    results: SearchResults
    timestamp: float


class SourceReference(TypedDict):
    """Source reference for citations."""

    title: str
    url: str
    description: str


class CacheStats(TypedDict):
    """Cache statistics and information."""

    total_entries: int
    cache_size_mb: float
    oldest_entry: Optional[str]
    newest_entry: Optional[str]
    hit_rate: Optional[float]
