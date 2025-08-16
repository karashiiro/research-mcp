import os
import asyncio
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import httpx
import sys


async def web_search(query: str, count: int = 10) -> Dict[str, Any]:
    """
    Perform a web search using the Brave Search API.
    
    Args:
        query: The search query string
        count: Number of results to return (default: 10, max: 20)
        
    Returns:
        Dictionary containing search results and metadata
        
    Raises:
        ValueError: If BRAVE_API_KEY environment variable is not set
        httpx.HTTPError: If the API request fails
    """
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
            
            return {
                "query": query,
                "results": results,
                "total_results": len(results),
                "api_response": data
            }
            
        except httpx.TimeoutException:
            raise httpx.HTTPError("Search request timed out")
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(f"Search API returned status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise httpx.HTTPError(f"Search request failed: {str(e)}")


def safe_print(text: str) -> None:
    """Print text safely by handling unicode encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII encoding for Windows console compatibility
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text)


# Example usage
async def main():
    load_dotenv()
    try:
        results = await web_search("python async programming", count=5)
        safe_print(f"Found {results['total_results']} results for: {results['query']}")
        
        for i, result in enumerate(results['results'], 1):
            safe_print(f"\n{i}. {result['title']}")
            safe_print(f"   URL: {result['url']}")
            safe_print(f"   Description: {result['description'][:100]}...")
            
    except Exception as e:
        safe_print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())