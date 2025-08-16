import os
import asyncio
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import httpx
import sys
from search_cache import get_cache


async def web_search(query: str, count: int = 10) -> Dict[str, Any]:
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
    # Check cache first
    cache = get_cache()
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
        "X-Subscription-Token": api_key
    }
    
    # Query parameters
    params = {
        "q": query,
        "count": min(count, 20),  # Brave API max is 20
        "search_lang": "en",
        "country": "US",
        "safesearch": "moderate",
        "freshness": "all"
    }
    
    # Retry logic with exponential backoff for rate limiting
    max_retries = 5
    base_delay = 1.0  # Start with 1 second
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract and format results
                results = []
                if "web" in data and "results" in data["web"]:
                    for result in data["web"]["results"]:
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "description": result.get("description", ""),
                            "published": result.get("age", ""),
                            "favicon": result.get("profile", {}).get("img", "")
                        })
                
                # Prepare results to return and cache
                search_results = {
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                    "api_response": data
                }
                
                # Cache the results for future use
                cache.set(query, count, search_results)
                
                return search_results
                
            except httpx.TimeoutException:
                raise httpx.HTTPError("Search request timed out")
            except httpx.HTTPStatusError as e:
                # Handle rate limiting with exponential backoff
                if e.response.status_code == 429 and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    print(f"Rate limited, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise httpx.HTTPError(f"Search API returned status {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise httpx.HTTPError(f"Search request failed: {str(e)}")
        
        # If we get here, all retries failed
        raise httpx.HTTPError("Maximum retries exceeded for rate limited requests")


# Example usage
async def main():
    load_dotenv()
    try:
        results = await web_search("python async programming", count=5)
        print(f"Found {results['total_results']} results for: {results['query']}")
        
        for i, result in enumerate(results['results'], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Description: {result['description'][:100]}...")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())