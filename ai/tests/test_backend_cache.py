"""
Unit Tests — Backend Tag-Based Response Cache
==============================================
Tests set, get, TTL expiration, key removal, and tag-based invalidation.
"""

import sys
import time
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.core.cache import ResponseCacheManager, cache_manager, invalidate_cache_tags


def test_cache_set_get_hit():
    cache = ResponseCacheManager()
    data = [{"id": "1", "name": "Store A"}, {"id": "2", "name": "Store B"}]
    cache.set("stores:list", data, ttl_seconds=10.0, tags=["stores"])

    cached = cache.get("stores:list")
    assert cached == data
    assert len(cached) == 2


def test_cache_ttl_expiration():
    cache = ResponseCacheManager()
    cache.set("short_lived", {"value": 42}, ttl_seconds=0.1, tags=["temp"])
    
    # Hit immediately
    assert cache.get("short_lived") == {"value": 42}
    
    # Sleep to expire
    time.sleep(0.15)
    assert cache.get("short_lived") is None


def test_cache_tag_invalidation():
    cache = ResponseCacheManager()
    cache.set("store:1", {"name": "Store 1"}, ttl_seconds=60.0, tags=["stores"])
    cache.set("store:2", {"name": "Store 2"}, ttl_seconds=60.0, tags=["stores"])
    cache.set("zone:1", {"name": "Zone A"}, ttl_seconds=60.0, tags=["zones"])
    cache.set("shelf:1", {"name": "Shelf 1"}, ttl_seconds=60.0, tags=["shelves", "stores"])

    assert cache.get("store:1") is not None
    assert cache.get("store:2") is not None
    assert cache.get("zone:1") is not None
    assert cache.get("shelf:1") is not None

    # Invalidate 'stores' tag
    evicted = cache.invalidate_tags("stores")
    assert evicted == 3  # store:1, store:2, and shelf:1 (tagged with stores)

    assert cache.get("store:1") is None
    assert cache.get("store:2") is None
    assert cache.get("shelf:1") is None
    assert cache.get("zone:1") is not None  # zone:1 remains intact


def test_global_invalidate_helper():
    cache_manager.set("test_key", "test_val", ttl_seconds=60.0, tags=["products"])
    assert cache_manager.get("test_key") == "test_val"

    invalidate_cache_tags("products")
    assert cache_manager.get("test_key") is None
