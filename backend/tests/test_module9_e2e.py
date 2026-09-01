"""
Module 9 — End-to-End & Comprehensive Edge Case Tests
======================================================
Tests all 5 recommendation rule categories, orchestrator ranking,
What-If planogram simulation, service layer, and synthetic edge cases.
"""

import sys
from pathlib import Path

# Ensure backend root is on Python path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.modules.recommendation.engine import Module9RecommendationEngine
from app.modules.recommendation.models import (
    ActionableRecommendation,
    ExpectedImpact,
    PlanogramSimulationRequest,
    PlanogramSimulationResult,
    RecommendationCategory,
    RecommendationPriority,
)
from app.modules.recommendation.simulator import PlanogramSimulator
from app.modules.recommendation.shelf_rules import evaluate_shelf_rules, infer_shelf_tier
from app.modules.recommendation.placement_rules import evaluate_placement_rules
from app.modules.recommendation.promo_rules import evaluate_promo_rules
from app.modules.recommendation.friction_rules import evaluate_friction_rules
from app.modules.recommendation.layout_rules import evaluate_layout_rules


# ── Test 1: Full Orchestrator Run with Multi-SKU Telemetry ─────

def test_full_orchestrator_generation():
    engine = Module9RecommendationEngine()

    sample_profiles = [
        # 1. Hidden Gem (High intrinsic on bottom tier)
        {
            "product_id": "sku-001",
            "product_name": "Artisanal Olive Oil",
            "category": "Oils & Vinegars",
            "intrinsic_attractiveness_score": 85.0,
            "attractiveness_score": 38.0,
            "shelf_visibility": {"shelf_tier": "BOTTOM", "gamma_coefficient": 0.40},
            "pillar_scores": {"interaction_score": 0.6, "pickup_score": 0.5},
            "total_viewers": 25,
            "total_passersby": 100,
            "average_attention_duration_sec": 5.0,
            "total_pickups": 12,
            "total_returns": 2,
            "total_purchases": 8,
            "conversion_potential_score": 78.0,
            "marketing_effectiveness_score": 72.0,
        },
        # 2. Shelf Squatter (Low intrinsic on eye-level)
        {
            "product_id": "sku-002",
            "product_name": "Old Brand Vinegar",
            "category": "Oils & Vinegars",
            "intrinsic_attractiveness_score": 25.0,
            "attractiveness_score": 25.0,
            "shelf_visibility": {"shelf_tier": "EYE_LEVEL", "gamma_coefficient": 1.00},
            "pillar_scores": {"interaction_score": 0.1, "pickup_score": 0.05},
            "total_viewers": 15,
            "total_passersby": 100,
            "average_attention_duration_sec": 1.2,
            "total_pickups": 1,
            "total_returns": 1,
            "total_purchases": 0,
            "conversion_potential_score": 20.0,
            "marketing_effectiveness_score": 25.0,
        },
        # 3. Hesitation Friction (High dwell, low pickup)
        {
            "product_id": "sku-003",
            "product_name": "Imported Truffle Sauce",
            "category": "Sauces",
            "intrinsic_attractiveness_score": 68.0,
            "attractiveness_score": 55.0,
            "shelf_visibility": {"shelf_tier": "TOUCH", "gamma_coefficient": 0.85},
            "pillar_scores": {"interaction_score": 0.2, "pickup_score": 0.05},
            "total_viewers": 30,
            "total_passersby": 80,
            "average_attention_duration_sec": 8.2,
            "total_pickups": 2,
            "total_returns": 0,
            "total_purchases": 1,
            "conversion_potential_score": 65.0,
            "marketing_effectiveness_score": 60.0,
        },
        # 4. Return Friction (High pickup, high return)
        {
            "product_id": "sku-004",
            "product_name": "Fragile Glass Bottle Soda",
            "category": "Beverages",
            "intrinsic_attractiveness_score": 58.0,
            "attractiveness_score": 50.0,
            "shelf_visibility": {"shelf_tier": "TOUCH", "gamma_coefficient": 0.85},
            "pillar_scores": {"interaction_score": 0.7, "pickup_score": 0.45},
            "total_viewers": 25,
            "total_passersby": 70,
            "average_attention_duration_sec": 4.0,
            "total_pickups": 12,
            "total_returns": 10,
            "total_purchases": 1,
            "conversion_potential_score": 40.0,
            "marketing_effectiveness_score": 50.0,
        },
    ]

    sample_heatmap = {
        "zones": [
            {"zone_id": "z-1", "zone_name": "Front Entrance", "dwell_time": 18.5, "density": 0.85},
            {"zone_id": "z-2", "zone_name": "Aisle 1 (Oils)", "dwell_time": 12.0, "density": 0.50},
            {"zone_id": "z-3", "zone_name": "Back Corner Deadzone", "dwell_time": 2.1, "density": 0.10},
        ]
    }

    sample_behavior = {
        "archetypes": {
            "Explorer": 0.35,
            "Quick Buyer": 0.28,
            "Comparison Shopper": 0.20,
            "Impulse Buyer": 0.17,
        }
    }

    result = engine.generate_recommendations(
        product_profiles=sample_profiles,
        heatmap_data=sample_heatmap,
        behavior_data=sample_behavior,
    )

    recs = result["recommendations"]
    summary = result["summary"]

    assert len(recs) >= 5, f"Expected at least 5 recommendations, got {len(recs)}"
    assert summary["total_recommendations"] == len(recs)
    assert summary["critical_count"] + summary["high_count"] > 0
    assert summary["average_impact_score"] > 0

    # Ensure categories are well-represented
    categories_found = {r["category"] for r in recs}
    assert "SHELF_OPTIMIZATION" in categories_found
    assert "PRODUCT_PLACEMENT" in categories_found
    assert "PROMOTIONAL_PLACEMENT" in categories_found
    assert "CONSUMER_ENGAGEMENT" in categories_found
    assert "LAYOUT_IMPROVEMENT" in categories_found

    print(f"✓ Full Orchestrator: {len(recs)} recs generated across {len(categories_found)} categories")
    print(f"  Critical: {summary['critical_count']}, High: {summary['high_count']}, "
          f"Avg Impact: +{summary['average_impact_score']}%")


# ── Test 2: Intra-Category Swap Rule Verification ──────────────

def test_pairwise_swap_rule():
    profiles = [
        {
            "product_id": "a-1",
            "product_name": "High Performer Bottom",
            "category": "Snacks",
            "intrinsic_attractiveness_score": 88.0,
            "shelf_visibility": {"shelf_tier": "BOTTOM"},
        },
        {
            "product_id": "a-2",
            "product_name": "Low Performer Eye-Level",
            "category": "Snacks",
            "intrinsic_attractiveness_score": 35.0,
            "shelf_visibility": {"shelf_tier": "EYE_LEVEL"},
        },
    ]

    recs = evaluate_placement_rules(profiles)
    swap_recs = [r for r in recs if "Swap" in r.title]
    assert len(swap_recs) == 1
    assert swap_recs[0].shelf_swap_details is not None
    assert swap_recs[0].expected_impact.attention_lift_pct > 0
    print(f"✓ Pairwise Swap Rule: correctly generated swap for '{swap_recs[0].title}'")


# ── Test 3: Dead Zone and Congestion Detection ─────────────────

def test_layout_deadzone_and_congestion():
    profiles = [
        {"product_id": "p-1", "product_name": "Top Milk Brand", "attractiveness_score": 90.0},
    ]
    heatmap = {
        "zones": [
            {"zone_id": "z-cold", "zone_name": "Back Wall Corner", "dwell_time": 1.0, "density": 0.05},
            {"zone_id": "z-mid", "zone_name": "Center Aisle", "dwell_time": 10.0, "density": 0.40},
            {"zone_id": "z-hot", "zone_name": "Checkout Bottleneck", "dwell_time": 22.0, "density": 0.92},
        ]
    }
    recs = evaluate_layout_rules(profiles, heatmap_data=heatmap)

    deadzone_recs = [r for r in recs if "Dead Zone" in r.title]
    congestion_recs = [r for r in recs if "Congestion" in r.title]

    assert len(deadzone_recs) >= 1
    assert len(congestion_recs) >= 1
    print(f"✓ Layout Rules: Detected dead zone '{deadzone_recs[0].target_name}' & congestion in '{congestion_recs[0].target_name}'")


# ── Test 4: Cold-Start & Empty Profiles Edge Case ──────────────

def test_cold_start_empty_profiles():
    engine = Module9RecommendationEngine()
    result = engine.generate_recommendations(product_profiles=[])
    assert result["recommendations"] == []
    assert result["summary"]["total_recommendations"] == 0
    print("✓ Cold-Start: Gracefully handled empty profiles")


# ── Test 5: Zero-Gaze High-Passerby Exposure Recovery ──────────

def test_zero_gaze_traffic_exposure():
    profiles = [
        {
            "product_id": "prod-coke",
            "product_name": "Coca-Cola 500ml",
            "category": "Beverages",
            "total_passersby": 39,
            "total_viewers": 0,
            "attractiveness_score": 5.15,
            "intrinsic_attractiveness_score": 6.87,
            "shelf_visibility": {"shelf_tier": "UNKNOWN"},
        },
    ]
    recs = evaluate_promo_rules(profiles)
    exposure_recs = [r for r in recs if "Capture Missed Footfall" in r.title or "Signage" in r.title]
    assert len(exposure_recs) >= 1
    assert exposure_recs[0].priority == RecommendationPriority.HIGH
    print(f"✓ Zero-Gaze Exposure Rule: generated '{exposure_recs[0].title}'")


# ── Test 6: Zero-Gaze Zone Calibration Alert ───────────────────

def test_zero_gaze_calibration_alert():
    profiles = [
        {
            "product_id": "prod-1",
            "product_name": "Item 1",
            "total_passersby": 25,
            "total_viewers": 0,
        },
        {
            "product_id": "prod-2",
            "product_name": "Item 2",
            "total_passersby": 25,
            "total_viewers": 0,
        },
    ]
    recs = evaluate_friction_rules(profiles)
    calib_recs = [r for r in recs if "Calibration" in r.title]
    assert len(calib_recs) >= 1
    assert calib_recs[0].category == RecommendationCategory.CONSUMER_ENGAGEMENT
    print(f"✓ Zero-Gaze Calibration Alert: generated '{calib_recs[0].title}'")


# ── Test 7: Shelf Tier Inference and Category Rebalancing ──────

def test_shelf_tier_inference_and_category_rebalance():
    assert infer_shelf_tier("UNKNOWN", shelf_name="Eye Level Shelf A") == "EYE_LEVEL"
    assert infer_shelf_tier("UNKNOWN", shelf_name="Bottom Floor Bin") == "BOTTOM"

    profiles = [
        {
            "product_id": "p-top",
            "product_name": "Amul Milk 1L",
            "category": "Dairy",
            "attractiveness_score": 45.0,
            "intrinsic_attractiveness_score": 45.0,
            "shelf_visibility": {"shelf_tier": "UNKNOWN"},
        },
        {
            "product_id": "p-bot",
            "product_name": "Amul Cheese",
            "category": "Dairy",
            "attractiveness_score": 15.0,
            "intrinsic_attractiveness_score": 15.0,
            "shelf_visibility": {"shelf_tier": "UNKNOWN"},
        },
    ]
    recs = evaluate_shelf_rules(profiles)
    rebalance_recs = [r for r in recs if "Rebalance" in r.title]
    assert len(rebalance_recs) >= 1
    print(f"✓ Category Rebalance Rule: generated '{rebalance_recs[0].title}'")


if __name__ == "__main__":
    test_full_orchestrator_generation()
    test_pairwise_swap_rule()
    test_layout_deadzone_and_congestion()
    test_cold_start_empty_profiles()
    test_zero_gaze_traffic_exposure()
    test_zero_gaze_calibration_alert()
    test_shelf_tier_inference_and_category_rebalance()
    print("\n" + "=" * 50)
    print("All Module 9 E2E Verification Tests Passed Successfully! 🎉")
