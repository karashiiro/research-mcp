"""
Tests for SearchCache module
"""

import json
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from research_orchestrator.types import SearchResults
from research_orchestrator.web.search.cache import SearchCache


class TestSearchCache:
    """Test cases for SearchCache functionality"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a SearchCache instance with temporary directory"""
        return SearchCache(cache_dir=temp_cache_dir, cache_ttl_hours=1)

    @pytest.fixture
    def sample_search_results(self) -> SearchResults:
        """Sample search results for testing"""
        return {
            "query": "AWS Bedrock throttling",
            "total_results": 3,
            "results": [
                {
                    "index": 1,
                    "title": "AWS Bedrock Throttling Guide",
                    "url": "https://example.com/guide1",
                    "description": "How to handle throttling",
                    "published": "2024-01-01",
                },
                {
                    "index": 2,
                    "title": "Rate Limiting Best Practices",
                    "url": "https://example.com/guide2",
                    "description": "Best practices for rate limiting",
                    "published": "2024-01-02",
                },
                {
                    "index": 3,
                    "title": "Exponential Backoff Implementation",
                    "url": "https://example.com/guide3",
                    "description": "How to implement backoff",
                    "published": "2024-01-03",
                },
            ],
        }  # type: ignore

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache initialization creates directories and metadata"""
        cache_dir = Path(temp_cache_dir) / "test_cache"
        SearchCache(cache_dir=str(cache_dir))

        # Check cache directory was created
        assert cache_dir.exists()

        # Check metadata file was created
        metadata_file = cache_dir / "cache_metadata.json"
        assert metadata_file.exists()

        # Check metadata file is valid JSON
        with metadata_file.open() as f:
            metadata = json.load(f)
            assert metadata == {}

    def test_cache_key_generation(self, cache):
        """Test cache key generation is consistent and handles case/whitespace"""
        key1 = cache._generate_cache_key("AWS Bedrock throttling", 10)
        key2 = cache._generate_cache_key("AWS BEDROCK THROTTLING", 10)
        key3 = cache._generate_cache_key("  aws bedrock throttling  ", 10)
        key4 = cache._generate_cache_key("AWS Bedrock throttling", 5)

        # Same query should generate same key (case insensitive, whitespace trimmed)
        assert key1 == key2 == key3

        # Different count should generate different key
        assert key1 != key4

    def test_cache_set_and_get(self, cache, sample_search_results):
        """Test basic cache set and get functionality"""
        query = "AWS Bedrock throttling"
        count = 10

        # Initially cache should be empty
        assert cache.get(query, count) is None

        # Set cache
        cache.set(query, count, sample_search_results)

        # Get from cache should return same results
        cached_results = cache.get(query, count)
        assert cached_results is not None
        assert cached_results == sample_search_results

    def test_cache_different_queries(self, cache, sample_search_results):
        """Test that different queries are cached separately"""
        query1 = "AWS Bedrock throttling"
        query2 = "AWS Bedrock pricing"
        count = 10

        # Cache first query
        cache.set(query1, count, sample_search_results)

        # Second query should not be cached
        assert cache.get(query2, count) is None

        # First query should still be cached
        assert cache.get(query1, count) == sample_search_results

    def test_cache_different_counts(self, cache, sample_search_results):
        """Test that different result counts are cached separately"""
        query = "AWS Bedrock throttling"

        # Cache with count=10
        cache.set(query, 10, sample_search_results)

        # Same query with different count should not be cached
        assert cache.get(query, 5) is None

        # Original count should still be cached
        assert cache.get(query, 10) == sample_search_results

    def test_cache_expiration(self, temp_cache_dir, sample_search_results):
        """Test cache expiration functionality"""
        # Create cache with very short TTL (1 second for testing)
        cache = SearchCache(cache_dir=temp_cache_dir, cache_ttl_hours=1 / 3600)
        query = "AWS Bedrock throttling"
        count = 10

        # Cache results
        cache.set(query, count, sample_search_results)

        # Should be available immediately
        assert cache.get(query, count) == sample_search_results

        # Wait for expiration (2 seconds to be safe)
        time.sleep(2)

        # Should be expired now
        assert cache.get(query, count) is None

    def test_cache_metadata_tracking(self, cache, sample_search_results):
        """Test that cache metadata is properly tracked"""
        query = "AWS Bedrock throttling"
        count = 10

        # Cache results
        cache.set(query, count, sample_search_results)

        # Check metadata was updated
        metadata = cache._load_metadata()
        assert len(metadata) == 1

        cache_key = cache._generate_cache_key(query, count)
        assert cache_key in metadata

        entry = metadata[cache_key]
        assert entry["query"] == query
        assert entry["count"] == count
        assert entry["results_count"] == 3
        assert "cached_at" in entry

    def test_cache_file_creation(self, cache, sample_search_results):
        """Test that cache files are properly created"""
        query = "AWS Bedrock throttling"
        count = 10

        # Cache results
        cache.set(query, count, sample_search_results)

        # Check cache file was created
        cache_key = cache._generate_cache_key(query, count)
        cache_filepath = cache._get_cache_filepath(cache_key)
        assert cache_filepath.exists()

        # Check file contents
        with cache_filepath.open() as f:
            cached_data = json.load(f)
            assert cached_data == sample_search_results

    def test_expired_entry_removal(self, temp_cache_dir, sample_search_results):
        """Test that expired entries are properly removed"""
        # Create cache with very short TTL
        cache = SearchCache(cache_dir=temp_cache_dir, cache_ttl_hours=1 / 3600)
        query = "AWS Bedrock throttling"
        count = 10

        # Cache results
        cache.set(query, count, sample_search_results)

        # Verify cache file exists
        cache_key = cache._generate_cache_key(query, count)
        cache_filepath = cache._get_cache_filepath(cache_key)
        assert cache_filepath.exists()

        # Wait for expiration
        time.sleep(2)

        # Try to get (should trigger cleanup)
        result = cache.get(query, count)
        assert result is None

        # Cache file should be removed
        assert not cache_filepath.exists()

        # Metadata should be updated
        metadata = cache._load_metadata()
        assert cache_key not in metadata

    def test_cleanup_expired_entries(self, temp_cache_dir, sample_search_results):
        """Test cleanup of all expired entries"""
        # Create cache with very short TTL
        cache = SearchCache(cache_dir=temp_cache_dir, cache_ttl_hours=1 / 3600)

        # Cache multiple results
        queries = ["query1", "query2", "query3"]
        for _, query in enumerate(queries):
            cache.set(query, 10, sample_search_results)

        # Verify all are cached
        for query in queries:
            assert cache.get(query, 10) == sample_search_results

        # Wait for expiration
        time.sleep(2)

        # Clean up expired entries
        cache.cleanup_expired()

        # All should be removed
        for query in queries:
            assert cache.get(query, 10) is None

        # Metadata should be empty
        metadata = cache._load_metadata()
        assert len(metadata) == 0

    def test_clear_all_cache(self, cache, sample_search_results):
        """Test clearing all cached results"""
        # Cache multiple results
        queries = ["query1", "query2", "query3"]
        for query in queries:
            cache.set(query, 10, sample_search_results)

        # Verify all are cached
        for query in queries:
            assert cache.get(query, 10) == sample_search_results

        # Clear all
        cache.clear_all()

        # All should be removed
        for query in queries:
            assert cache.get(query, 10) is None

        # Metadata should be empty
        metadata = cache._load_metadata()
        assert len(metadata) == 0

    def test_corrupted_metadata_handling(self, cache, sample_search_results):
        """Test handling of corrupted metadata file"""
        query = "AWS Bedrock throttling"
        count = 10

        # Cache some results first
        cache.set(query, count, sample_search_results)

        # Corrupt the metadata file
        with cache.metadata_file.open("w") as f:
            f.write("invalid json content")

        # Should handle corrupted metadata gracefully
        cache.get(query, count)
        # May return None due to corrupted metadata

        # Should be able to set new cache entries
        cache.set("new query", 10, sample_search_results)

    def test_missing_cache_file_handling(self, cache, sample_search_results):
        """Test handling of missing cache file with metadata entry"""
        query = "AWS Bedrock throttling"
        count = 10

        # Cache results
        cache.set(query, count, sample_search_results)

        # Delete the cache file but leave metadata
        cache_key = cache._generate_cache_key(query, count)
        cache_filepath = cache._get_cache_filepath(cache_key)
        cache_filepath.unlink()

        # Should handle missing file gracefully
        result = cache.get(query, count)
        assert result is None

    def test_invalid_datetime_handling(self, cache):
        """Test handling of invalid datetime in metadata"""
        # Create metadata with invalid datetime
        cache_key = "test_key"
        metadata = {
            cache_key: {
                "query": "test",
                "count": 10,
                "cached_at": "invalid_datetime",
                "results_count": 5,
            }
        }
        cache._save_metadata(metadata)

        # Should consider invalid datetime as expired
        assert cache._is_cache_expired("invalid_datetime") is True

    @patch("builtins.print")
    def test_cache_console_output(self, mock_print, cache, sample_search_results):
        """Test that cache operations produce appropriate console output"""
        query = "AWS Bedrock throttling"
        count = 10

        # Set cache should print cache message
        cache.set(query, count, sample_search_results)
        mock_print.assert_called_with(f"💾 Cached results for: {query}")

        # Get cache should print cache hit message
        cache.get(query, count)
        mock_print.assert_called_with(f"🔄 Using cached results for: {query}")

    def test_cache_with_special_characters(self, cache, sample_search_results):
        """Test cache with special characters in query"""
        special_query = "AWS Bedrock: throttling & rate-limiting (2024)!"
        count = 10

        # Should handle special characters
        cache.set(special_query, count, sample_search_results)
        result = cache.get(special_query, count)
        assert result == sample_search_results

    def test_cache_with_unicode(self, cache, sample_search_results):
        """Test cache with unicode characters"""
        unicode_query = "AWS Bedrock 限制 throttling 🚀"
        count = 10

        # Should handle unicode characters
        cache.set(unicode_query, count, sample_search_results)
        result = cache.get(unicode_query, count)
        assert result == sample_search_results

    def test_cache_persistence_across_instances(
        self, temp_cache_dir, sample_search_results
    ):
        """Test that cache persists across SearchCache instances"""
        query = "AWS Bedrock throttling"
        count = 10

        # Create first cache instance and store data
        cache1 = SearchCache(cache_dir=temp_cache_dir)
        cache1.set(query, count, sample_search_results)

        # Create second cache instance
        cache2 = SearchCache(cache_dir=temp_cache_dir)

        # Should be able to retrieve from second instance
        result = cache2.get(query, count)
        assert result == sample_search_results

    def test_cache_ttl_configuration(self, temp_cache_dir):
        """Test different TTL configurations"""
        # Test various TTL values
        ttl_hours = [1, 24, 168]  # 1 hour, 1 day, 1 week

        for ttl in ttl_hours:
            cache = SearchCache(cache_dir=temp_cache_dir, cache_ttl_hours=ttl)
            assert cache.cache_ttl == timedelta(hours=ttl)

    def test_large_search_results(self, cache):
        """Test cache with large search results"""
        # Create large search results
        large_results: SearchResults = {
            "query": "large test query",
            "total_results": 1000,
            "results": [  # type: ignore
                {
                    "index": i,
                    "title": f"Large Result {i}" * 10,  # Make title longer
                    "url": f"https://example.com/large-result-{i}",
                    "description": f"This is a large description for result {i}. " * 20,
                    "published": "2024-01-01",
                }
                for i in range(100)  # 100 large results
            ],
        }

        query = "large test query"
        count = 100

        # Should handle large results
        cache.set(query, count, large_results)
        result = cache.get(query, count)
        assert result == large_results
        assert len(result["results"]) == 100
