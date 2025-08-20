"""
Search Result Caching Module
Provides caching functionality to reduce redundant API calls
"""

import json
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..types import SearchResults


class SearchCache:
    """
    Simple file-based cache for search results to reduce API calls
    """

    def __init__(self, cache_dir: str = "cache", cache_ttl_hours: int = 24):
        """
        Initialize the search cache

        Args:
            cache_dir: Directory to store cache files
            cache_ttl_hours: How many hours to keep cached results (default: 24)
        """
        self.cache_dir = cache_dir
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Create cache metadata file if it doesn't exist
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        if not os.path.exists(self.metadata_file):
            self._save_metadata({})

    def _generate_cache_key(self, query: str, count: int) -> str:
        """Generate a unique cache key for a search query"""
        # Create a hash of the query and parameters
        key_data = f"{query.lower().strip()}_{count}"
        cache_key = hashlib.md5(key_data.encode()).hexdigest()
        return cache_key

    def _get_cache_filepath(self, cache_key: str) -> str:
        """Get the full filepath for a cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata"""
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache metadata: {e}")

    def _is_cache_expired(self, cached_time: str) -> bool:
        """Check if a cached result has expired"""
        try:
            cached_datetime = datetime.fromisoformat(cached_time)
            return datetime.now() - cached_datetime > self.cache_ttl
        except (ValueError, TypeError):
            return True  # If we can't parse the time, consider it expired

    def get(self, query: str, count: int = 10) -> Optional[SearchResults]:
        """
        Get cached search results if available and not expired

        Args:
            query: Search query
            count: Number of results requested

        Returns:
            Cached search results or None if not found/expired
        """
        cache_key = self._generate_cache_key(query, count)
        cache_filepath = self._get_cache_filepath(cache_key)

        # Check if cache file exists
        if not os.path.exists(cache_filepath):
            return None

        # Check metadata for expiration
        metadata = self._load_metadata()
        if cache_key not in metadata:
            return None

        # Check if expired
        if self._is_cache_expired(metadata[cache_key]["cached_at"]):
            # Clean up expired cache
            self._remove_expired_entry(cache_key)
            return None

        # Load and return cached results
        try:
            with open(cache_filepath, "r", encoding="utf-8") as f:
                cached_results = json.load(f)

            print(f"🔄 Using cached results for: {query}")
            return cached_results

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load cached results for {query}: {e}")
            return None

    def set(self, query: str, count: int, results: SearchResults):
        """
        Cache search results

        Args:
            query: Search query
            count: Number of results requested
            results: Search results to cache
        """
        cache_key = self._generate_cache_key(query, count)
        cache_filepath = self._get_cache_filepath(cache_key)

        try:
            # Save the results
            with open(cache_filepath, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            # Update metadata
            metadata = self._load_metadata()
            metadata[cache_key] = {
                "query": query,
                "count": count,
                "cached_at": datetime.now().isoformat(),
                "results_count": results.get("total_results", 0),
            }
            self._save_metadata(metadata)

            print(f"💾 Cached results for: {query}")

        except Exception as e:
            print(f"Warning: Failed to cache results for {query}: {e}")

    def _remove_expired_entry(self, cache_key: str):
        """Remove an expired cache entry"""
        try:
            cache_filepath = self._get_cache_filepath(cache_key)
            if os.path.exists(cache_filepath):
                os.remove(cache_filepath)

            # Update metadata
            metadata = self._load_metadata()
            if cache_key in metadata:
                del metadata[cache_key]
                self._save_metadata(metadata)

        except Exception as e:
            print(f"Warning: Failed to remove expired cache entry: {e}")

    def cleanup_expired(self):
        """Remove all expired cache entries"""
        metadata = self._load_metadata()
        expired_keys = []

        for cache_key, entry in metadata.items():
            if self._is_cache_expired(entry["cached_at"]):
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            self._remove_expired_entry(cache_key)

        if expired_keys:
            print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

    def clear_all(self):
        """Clear all cached results"""
        try:
            # Remove all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.cache_dir, filename)
                    os.remove(filepath)

            # Reset metadata
            self._save_metadata({})
            print("🗑️ Cleared all cached search results")

        except Exception as e:
            print(f"Warning: Failed to clear cache: {e}")


# Global cache instance
_cache_instance = None


def get_cache() -> SearchCache:
    """Get the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SearchCache()
    return _cache_instance
