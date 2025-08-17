"""
Search and Caching Package

Provides web search capabilities with intelligent caching for research operations.
"""

from .web_search import web_search
from .cache import SearchCache, get_cache

__all__ = ["web_search", "SearchCache", "get_cache"]