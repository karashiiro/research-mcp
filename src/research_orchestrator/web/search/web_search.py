import asyncio
import itertools
import os

import httpx
from httpcore._async.connection import exponential_backoff

from ...types import SearchResultItem, SearchResults
from .cache import SearchCache


async def web_search(
    query: str, count: int = 10, *, cache: SearchCache
) -> SearchResults:
    """
    Perform a web search using the Brave Search API with caching.

    Args:
        query: The search query string
        count: Number of results to return (default: 10, max: 20)

    Returns:
        Dictionary containing search results and metadata

    Raises:
        ValueError: If BRAVE_API_KEY environment variable is not set
        httpx.HTTPError: If the API request fails
    """
    cached_results = cache.get(query, count)
    if cached_results is not None:
        return cached_results

    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        raise ValueError("BRAVE_API_KEY environment variable is required")

    # Brave Search API endpoint
    url = "https://api.search.brave.com/res/v1/web/search"

    # Request headers
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    # Query parameters
    params = {
        "q": str(query),
        "count": str(min(count, 20)),  # Brave API max is 20
        "search_lang": "en",
        "country": "US",
        "safesearch": "moderate",
        "freshness": "all",
    }

    # Retry logic with exponential backoff for rate limiting
    max_retries = 5

    async with httpx.AsyncClient(timeout=300.0) as client:
        for attempt, delay in enumerate(
            itertools.islice(exponential_backoff(factor=1.0), max_retries + 1)
        ):
            await asyncio.sleep(delay)  # 0, 1, 2, 4, 8, 16 seconds

            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Extract and format results
                results: list[SearchResultItem] = []
                if "web" in data and "results" in data["web"]:
                    for result in data["web"]["results"]:
                        results.append(
                            SearchResultItem(
                                title=result.get("title", ""),
                                url=result.get("url", ""),
                                description=result.get("description", ""),
                                published=result.get("age", ""),
                                favicon=result.get("profile", {}).get("img", ""),
                            )
                        )

                # Prepare results to return and cache
                search_results = SearchResults(
                    query=query,
                    results=results,
                    total_results=len(results),
                    api_response=data,
                )

                # Cache the results for future use
                cache.set(query, count, search_results)

                return search_results

            except httpx.TimeoutException as e:
                raise httpx.HTTPError("Search request timed out") from e
            except httpx.HTTPStatusError as e:
                # Handle rate limiting with exponential backoff
                if e.response.status_code == 429 and attempt < max_retries:
                    print(
                        f"Rate limited, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    continue
                else:
                    raise httpx.HTTPError(
                        f"Search API returned status {e.response.status_code}: {e.response.text}"
                    ) from e
            except Exception as e:
                raise httpx.HTTPError(f"Search request failed: {str(e)}") from e

        # If we get here, all retries failed
        raise httpx.HTTPError("Maximum retries exceeded for rate limited requests")
