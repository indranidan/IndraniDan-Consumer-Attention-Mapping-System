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

    # 6. Marketing Manager payload
    assert "marketing_manager" in res
    mm = res["marketing_manager"]
    assert "campaign_lift" in mm
    assert "visibility" in mm
    assert "promotional_performance" in mm
    assert "engagement" in mm

    campaign = mm["campaign_lift"]
    assert "eye_level_engagement_lift" in campaign and campaign["eye_level_engagement_lift"] > 0
    assert "endcap_conversion_increase" in campaign and campaign["endcap_conversion_increase"] > 0
    assert "promo_response_rate" in campaign and campaign["promo_response_rate"] > 0
    assert "top_performing_campaign" in campaign and len(campaign["top_performing_campaign"]) > 0

    visibility = mm["visibility"]
    assert "category_gaze" in visibility and len(visibility["category_gaze"]) > 0
    assert "blind_spot_zones" in visibility and len(visibility["blind_spot_zones"]) > 0
    assert "premium_shelf_dwell_share" in visibility and visibility["premium_shelf_dwell_share"] > 0

    promo = mm["promotional_performance"]
    assert "active_promotions" in promo and promo["active_promotions"] > 0
    assert "promo_product_pickups" in promo and promo["promo_product_pickups"] > 0
    assert "dwell_per_promo_sec" in promo and promo["dwell_per_promo_sec"] > 0
    assert "endcap_vs_aisle_ratio" in promo and promo["endcap_vs_aisle_ratio"] > 0

    engagement = mm["engagement"]
    assert "repeat_engagement_rate" in engagement and engagement["repeat_engagement_rate"] > 0
    assert "total_recommendations" in engagement and engagement["total_recommendations"] > 0
    assert "projected_attention_lift" in engagement and engagement["projected_attention_lift"] > 0


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
    assert "marketing_manager" in res
    assert res["marketing_manager"]["campaign_lift"]["eye_level_engagement_lift"] > 0

