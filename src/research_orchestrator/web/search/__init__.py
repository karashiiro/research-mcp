"""
Search and Caching Package

Provides web search capabilities with intelligent caching for research operations.
"""

from research_orchestrator.web.search.cache import SearchCache
from research_orchestrator.web.search.web_search import web_search

__all__ = ["web_search", "SearchCache"]
