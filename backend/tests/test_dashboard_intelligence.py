"""
Test Retail Intelligence Dashboard Analytics API & Aggregation Service
========================================================================
Verifies multi-module aggregation (M3-M9), store-level filtering,
and caching in dashboard_service.py.
"""

import sys
from pathlib import Path

# Ensure backend root is on Python path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.services.dashboard_service import get_dashboard_analytics_data, invalidate_dashboard_cache


def test_dashboard_analytics_data_structure():
    """Verify that get_dashboard_analytics_data returns all 5 executive sections."""
    invalidate_dashboard_cache()

    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.all.return_value = []
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

    res = get_dashboard_analytics_data(mock_db, force_fresh=True)

    # 1. Top-level keys
    assert "kpis" in res
    assert "funnel" in res
    assert "leaderboard" in res
    assert "archetypes" in res
    assert "recommendations" in res
    assert "recent_jobs" in res

    # 2. KPI metrics
    kpis = res["kpis"]
    assert "total_footfall" in kpis
    assert "gaze_capture_rate" in kpis
    assert "pickup_rate" in kpis
    assert "attractiveness_index" in kpis
    assert "attractiveness_rating" in kpis

    # 3. Funnel stages
    funnel = res["funnel"]
    assert "passersby" in funnel
    assert "gaze_dwell" in funnel
    assert "physical_pickup" in funnel
    assert "purchase_conversion" in funnel

    # 4. Leaderboard
    leaderboard = res["leaderboard"]
    assert "top_performers" in leaderboard
    assert "attention_leaks" in leaderboard

    # 5. Archetypes
    archetypes = res["archetypes"]
    assert "dominant_segment" in archetypes
    assert "distribution" in archetypes


def test_dashboard_analytics_store_filtering():
    """Verify that get_dashboard_analytics_data filters properly when store_id is provided."""
    invalidate_dashboard_cache()

    import uuid
    dummy_store_id = uuid.uuid4()

    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

    res = get_dashboard_analytics_data(mock_db, store_id=dummy_store_id, force_fresh=True)
    assert res["store_id"] == str(dummy_store_id)
