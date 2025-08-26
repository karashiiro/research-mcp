"""
Research Tools for Agents

Python tools that can be used by research agents for direct web searching and content fetching.
"""

# Import AgentManager with TYPE_CHECKING to avoid circular import
from typing import TYPE_CHECKING, Any

from strands import tool

from research_orchestrator.search.cache import SearchCache
from research_orchestrator.search.web_search import web_search
from research_orchestrator.types import SearchResults
from research_orchestrator.utils import get_blocked_url_error, is_url_blocked
from research_orchestrator.web import WebContentFetcher

if TYPE_CHECKING:
    from research_orchestrator.agents import AgentManager


def create_search_tools(
    agent_manager: "AgentManager", cache: SearchCache, web_fetcher: WebContentFetcher
):
    """Create search tools."""

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
            search_results: SearchResults = await web_search(query, count, cache=cache)

            # Convert to agent-friendly format
            formatted_results: dict[str, Any] = {
                "query": search_results["query"],
                "total_results": search_results["total_results"],
                "results": [],
            }

            # Format each result for easy consumption by agents
            results_list = []
            for i, result in enumerate(search_results["results"], 1):
                url = result["url"]
                results_list.append(
                    {
                        "index": i,
                        "title": result["title"],
                        "url": url,
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
    async def fetch_web_content(urls: list[str]) -> list[dict[str, Any]]:
        """
        Fetch content from multiple web URLs concurrently.

        Uses intelligent HTML parsing, noise removal, and retry logic to provide
        clean, readable content from web pages. Fetches all URLs in parallel for efficiency.

        Args:
            urls: List of URLs to fetch content from (limit: 5 URLs max per call)

        Returns:
            List of dictionaries containing extracted content and metadata for each URL

        Example usage:
            urls = ["https://example.com/guide1", "https://example.com/guide2"]
            results = await fetch_web_content(urls)
            for result in results:
                if result['success']:
                    print(f"Title: {result['title']}")
                    print(f"Content: {result['content']}")
                else:
                    print(f"Failed to fetch {result['url']}: {result['error']}")
        """
        # Filter out blocked URLs
        filtered_urls = []
        blocked_results = []

        for url in urls[:5]:  # Limit to 5 URLs max
            if is_url_blocked(url):
                blocked_results.append(get_blocked_url_error(url))
            else:
                filtered_urls.append(url)

        # Fetch content from non-blocked URLs
        if filtered_urls:
            fetch_results = await web_fetcher.fetch_content_batch(filtered_urls)
        else:
            fetch_results = []

        # Combine blocked and fetched results
        all_results = blocked_results + fetch_results

        # Track only successful URLs for additional sources
        for result in all_results:
            if result.get("success"):
                agent_manager.tracked_urls.add(result["url"])

        return all_results

    return [search_web, fetch_web_content]
