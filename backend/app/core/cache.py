"""
High-Performance Response & Query Cache
=======================================
Provides sub-millisecond in-memory & Redis response caching with
tag-indexed eviction for automatic cache invalidation on database mutations.
"""

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger("app.cache")

try:
    import redis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class CacheEntry:
    __slots__ = ("data", "expires_at", "tags")

    def __init__(self, data: Any, expires_at: float, tags: Set[str]):
        self.data = data
        self.expires_at = expires_at
        self.tags = tags

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at


class ResponseCacheManager:
    """Thread-safe, tag-indexed cache manager with sub-millisecond in-memory lookup."""

    def __init__(self, redis_url: Optional[str] = None):
        self._memory_store: Dict[str, CacheEntry] = {}
        self._tag_to_keys: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._redis_client = None

        if _REDIS_AVAILABLE and redis_url:
            try:
                self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info("Connected to Redis cache store")
            except Exception as e:
                logger.warning(f"Redis cache connection unavailable ({e}), using in-memory store")
                self._redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached payload if valid and not expired. Returns None on cache miss."""
        now = time.time()
        with self._lock:
            entry = self._memory_store.get(key)
            if entry is not None:
                if entry.is_expired(now):
                    self._remove_key(key)
                    return None
                return entry.data

        if self._redis_client is not None:
            try:
                val = self._redis_client.get(f"cache:{key}")
                if val:
                    data = json.loads(val)
                    # Sync to memory cache for instantaneous 0ms local reads
                    with self._lock:
                        self._memory_store[key] = CacheEntry(data, now + 30.0, set())
                    return data
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        return None

    def set(
        self,
        key: str,
        data: Any,
        ttl_seconds: float = 60.0,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Store payload with TTL and associate with one or more invalidation tags."""
        now = time.time()
        expires_at = now + ttl_seconds
        tag_set = set(tags or [])

        with self._lock:
            self._memory_store[key] = CacheEntry(data, expires_at, tag_set)
            for tag in tag_set:
                if tag not in self._tag_to_keys:
                    self._tag_to_keys[tag] = set()
                self._tag_to_keys[tag].add(key)

        if self._redis_client is not None:
            try:
                val = json.dumps(data, default=str)
                self._redis_client.setex(f"cache:{key}", int(ttl_seconds), val)
                for tag in tag_set:
                    self._redis_client.sadd(f"tag:{tag}", key)
            except Exception as e:
                logger.debug(f"Redis set error: {e}")

    def invalidate_tags(self, *tags: str) -> int:
        """Evict all cached entries associated with the specified tags. Returns count of evicted keys."""
        evicted_count = 0
        keys_to_remove: Set[str] = set()

        with self._lock:
            for tag in tags:
                matched_keys = self._tag_to_keys.pop(tag, set())
                keys_to_remove.update(matched_keys)

            for key in keys_to_remove:
                if key in self._memory_store:
                    self._memory_store.pop(key, None)
                    evicted_count += 1

        if self._redis_client is not None:
            try:
                pipe = self._redis_client.pipeline()
                for tag in tags:
                    tag_keys = self._redis_client.smembers(f"tag:{tag}")
                    for k in tag_keys:
                        pipe.delete(f"cache:{k}")
                    pipe.delete(f"tag:{tag}")
                pipe.execute()
            except Exception as e:
                logger.debug(f"Redis tag invalidation error: {e}")

        logger.debug(f"Invalidated cache tags {tags}: {evicted_count} keys evicted")
        return evicted_count

    def invalidate_key(self, key: str) -> bool:
        """Explicitly evict a single cache key."""
        with self._lock:
            return self._remove_key(key)

    def _remove_key(self, key: str) -> bool:
        entry = self._memory_store.pop(key, None)
        if entry:
            for tag in entry.tags:
                if tag in self._tag_to_keys:
                    self._tag_to_keys[tag].discard(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all in-memory and Redis caches."""
        with self._lock:
            self._memory_store.clear()
            self._tag_to_keys.clear()
        if self._redis_client is not None:
            try:
                self._redis_client.flushdb()
            except Exception:
                pass


# Global singleton instance
cache_manager = ResponseCacheManager()


def invalidate_cache_tags(*tags: str) -> int:
    """Helper function to invalidate cache tags across the application."""
    return cache_manager.invalidate_tags(*tags)
