"""
Unit Tests & Latency Benchmark — Dashboard Query Optimization & Caching
========================================================================
Tests single-roundtrip stats, batch analytics retrieval, and TTL caching.
"""

import sys
import time
from pathlib import Path
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.database.database import Base
from app.models.store import Store
from app.models.camera import Camera
from app.models.shelf import Shelf
from app.models.product import Product
from app.models.ai_job import AIJob
from app.services.dashboard_service import (
    get_dashboard_analytics_data,
    invalidate_dashboard_cache,
    _dashboard_cache,
)
from app.api.dashboard import get_dashboard_stats


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_dashboard_stats_single_query(in_memory_db):
    # Seed dummy data
    store = Store(name="Flagship Store", store_code="STR-001", address="123 Main St", created_by=uuid.uuid4())
    in_memory_db.add(store)
    in_memory_db.commit()



    stats = get_dashboard_stats(current_user=None, db=in_memory_db)
    assert stats.stores == 1
    assert stats.zones == 0
    assert stats.shelves == 0
    assert stats.products == 0
    assert stats.cameras == 0


def test_dashboard_analytics_batch_and_cache(in_memory_db):
    # 1. Invalidate cache
    invalidate_dashboard_cache()
    assert _dashboard_cache["data"] is None

    # 2. Execute dashboard analytics query with session
    t0 = time.perf_counter()
    data1 = get_dashboard_analytics_data(in_memory_db, force_fresh=True)
    t_first = (time.perf_counter() - t0) * 1000

    assert "overview" in data1
    assert "top_shelves" in data1
    assert "store_performance" in data1
    assert "recent_jobs" in data1
    assert "traffic_trend" in data1

    # 3. Test Cache Hit (sub-millisecond)
    t1 = time.perf_counter()
    data2 = get_dashboard_analytics_data(in_memory_db, force_fresh=False)
    t_cached = (time.perf_counter() - t1) * 1000

    assert data2 == data1
    assert t_cached < 10.0, f"Expected cache retrieval < 10ms, got {t_cached:.2f}ms"
    print(f"[PASS] Cold Query: {t_first:.2f}ms | Cached Hit: {t_cached:.4f}ms")

    # 4. Test Invalidation
    invalidate_dashboard_cache()
    assert _dashboard_cache["data"] is None
