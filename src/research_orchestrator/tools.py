"""
Research Tools for Agents

Python tools that can be used by research agents for direct web searching and content fetching.
"""

from typing import Any

from strands import tool

from .search.web_search import web_search
from .types import SearchResults
from .web import WebContentFetcher

# Create a shared content fetcher instance
_content_fetcher = WebContentFetcher()


@tool
async def search_web(query: str, count: int = 5) -> dict[str, Any]:
    """
    Perform a web search and return results.

    Note: There is no hard limit on the number of searches you can perform.
    Use as many searches as needed to gather comprehensive information.

    Args:
        query: The search query string
        count: Number of results to return (default: 5, max: 20)

    Returns:
        Dictionary containing search results with title, url, and description

    Example usage:
        results = await search_web("My Very Interesting Topic")
        for i, result in enumerate(results["results"], 1):
            print(f"[{i}] {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Description: {result['description']}")
    """
    try:
        # Perform the web search
        search_results: SearchResults = await web_search(query, count)

        # Convert to agent-friendly format
        formatted_results: dict[str, Any] = {
            "query": search_results["query"],
            "total_results": search_results["total_results"],
            "results": [],
        }

        # Format each result for easy consumption by agents
        results_list = []
        for i, result in enumerate(search_results["results"], 1):
            results_list.append(
                {
                    "index": i,
                    "title": result["title"],
                    "url": result["url"],
                    "description": result["description"],
                    "published": result.get("published", ""),
                }
            )
        formatted_results["results"] = results_list

        return formatted_results

    except Exception as e:
        # Return error in a format agents can handle
        return {
            "query": query,
            "total_results": 0,
            "results": [],
            "error": f"Search failed: {str(e)}",
        }


@tool
async def fetch_web_content(
    url: str,
    prompt: str = "Extract the main content and key information from this page",
) -> dict[str, Any]:
    """
    Fetch content from a web URL and extract key information.

    Uses intelligent HTML parsing, noise removal, and retry logic to provide
    clean, readable content from web pages.

    Args:
        url: The URL to fetch content from
        prompt: Optional prompt to guide content extraction (default: general extraction)

    Returns:
        Dictionary containing extracted content and metadata

    Example usage:
        content = await fetch_web_content("https://example.com/guide", "Extract team composition recommendations")
        print(f"Content: {content['content']}")
        print(f"Title: {content['title']}")
    """
    return await _content_fetcher.fetch_content(url, prompt)


def get_research_tools() -> list:
    """
    Get the list of tools available to research agents.

    Returns:
        List of Python tools that can be used by agents
    """
    return [search_web, fetch_web_content]
