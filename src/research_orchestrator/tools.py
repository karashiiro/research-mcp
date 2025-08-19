"""
Research Tools for Agents

Python tools that can be used by research agents for direct web searching.
"""

from typing import Dict, Any, List
from strands import tool

from .types import SearchResults
from .search.web_search import web_search


@tool
async def search_web(query: str, count: int = 5) -> Dict[str, Any]:
    """
    Perform a web search and return results.

    Args:
        query: The search query string
        count: Number of results to return (default: 5, max: 20)

    Returns:
        Dictionary containing search results with title, url, and description

    Example usage:
        results = await search_web("Genshin Impact Imaginarium Theatre guides")
        for i, result in enumerate(results["results"], 1):
            print(f"[{i}] {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Description: {result['description']}")
    """
    try:
        # Perform the web search
        search_results: SearchResults = await web_search(query, count)

        # Convert to agent-friendly format
        formatted_results: Dict[str, Any] = {
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


def get_research_tools() -> List:
    """
    Get the list of tools available to research agents.

    Returns:
        List of Python tools that can be used by agents
    """
    return [search_web]
