"""
Utility functions for research orchestration.

Common helper functions used across the research system.
"""

from typing import Any


def is_url_blocked(url: str) -> bool:
    """
    Check if a URL should be blocked from fetching.

    Args:
        url: The URL to check

    Returns:
        True if the URL is blocked, False otherwise
    """
    # Domains that are blocked for fetching
    blocked_domains = [
        # We'll get flagged by jina.ai if we call them anonymously too often,
        # and GPT-OSS has a strange tendency to immediately try to fetch from
        # them if it gets blocked on anything else.
        "r.jina.ai",
    ]

    return any(blocked_domain in url for blocked_domain in blocked_domains)


def get_blocked_url_error(url: str) -> dict[str, Any]:
    """
    Create a standardized error response for blocked URLs.

    Args:
        url: The blocked URL

    Returns:
        Error response dictionary
    """
    return {
        "url": url,
        "success": False,
        "error": "URL blocked - domain not allowed for fetching",
        "content": "",
        "title": "",
    }
