"""
Module 9 — Recommendation Engine Tests
=========================================
Unit tests for:
- PlanogramSimulator: tier swap accuracy, bounding, idempotency
- Shelf rules: Hidden Gem detection, Shelf Squatter detection
- Friction rules: funnel drop-off diagnosis
- Model serialization
"""

import sys
from pathlib import Path

# Ensure backend is on path for isolated test runs
_backend = str(Path(__file__).resolve().parent.parent)
if _backend not in sys.path:
    sys.path.insert(0, _backend)


# ── Simulator Tests ──────────────────────────────────────────────

from app.modules.recommendation.simulator import PlanogramSimulator
from app.modules.recommendation.models import (
    PlanogramSimulationRequest,
    RecommendationCategory,
    RecommendationPriority,
    ExpectedImpact,
    ActionableRecommendation,
    Module9Summary,
)


def test_simulator_bottom_to_eye_level():
    """Moving from BOTTOM to EYE_LEVEL should improve scores."""
    req = PlanogramSimulationRequest(
        product_id="prod-001",
        current_shelf_tier="BOTTOM",
        target_shelf_tier="EYE_LEVEL",
        current_facing_count=1,
        target_facing_count=1,
        current_attractiveness_score=40.0,
        current_intrinsic_score=72.0,
    )
    result = PlanogramSimulator.simulate(req)

    assert result.is_improvement is True
    assert result.simulated_gamma > result.original_gamma
    assert result.simulated_attractiveness_score > result.original_attractiveness_score
    assert result.attention_lift_pct > 0
    assert result.conversion_lift_pct > 0
    print(f"✓ Bottom→EyeLevel: att_lift={result.attention_lift_pct}%, "
          f"score {result.original_attractiveness_score} → {result.simulated_attractiveness_score}")


def test_simulator_eye_level_to_bottom():
    """Moving from EYE_LEVEL to BOTTOM should worsen scores."""
    req = PlanogramSimulationRequest(
        product_id="prod-002",
        current_shelf_tier="EYE_LEVEL",
        target_shelf_tier="BOTTOM",
        current_facing_count=2,
        target_facing_count=2,
        current_attractiveness_score=80.0,
        current_intrinsic_score=80.0,
    )
    result = PlanogramSimulator.simulate(req)

    assert result.is_improvement is False
    assert result.attention_lift_pct < 0
    assert result.simulated_attractiveness_score < result.original_attractiveness_score
    print(f"✓ EyeLevel→Bottom: att_lift={result.attention_lift_pct}%, "
          f"score {result.original_attractiveness_score} → {result.simulated_attractiveness_score}")


def test_simulator_same_tier_no_change():
    """Moving to same tier with same facings should yield minimal change."""
    req = PlanogramSimulationRequest(
        product_id="prod-003",
        current_shelf_tier="TOUCH",
        target_shelf_tier="TOUCH",
        current_facing_count=3,
        target_facing_count=3,
        current_attractiveness_score=55.0,
        current_intrinsic_score=60.0,
    )
    result = PlanogramSimulator.simulate(req)

    assert abs(result.attention_lift_pct) < 0.01
    assert abs(result.simulated_attractiveness_score - result.original_attractiveness_score) < 0.01
    assert result.facing_change == 0
    print(f"✓ Same tier: att_lift={result.attention_lift_pct}% (expected ~0)")


def test_simulator_scores_bounded():
    """Simulated scores must stay within [0, 100]."""
    req = PlanogramSimulationRequest(
        product_id="prod-004",
        current_shelf_tier="BOTTOM",
        target_shelf_tier="EYE_LEVEL",
        current_facing_count=1,
        target_facing_count=5,
        current_attractiveness_score=95.0,
        current_intrinsic_score=99.0,
    )
    result = PlanogramSimulator.simulate(req)

    assert 0.0 <= result.simulated_visibility_score <= 100.0
    assert 0.0 <= result.simulated_attractiveness_score <= 100.0
    print(f"✓ Bounded: visibility={result.simulated_visibility_score}, "
          f"attractiveness={result.simulated_attractiveness_score}")


def test_simulator_facing_increase_lift():
    """Increasing facing count should provide marginal lift."""
    req = PlanogramSimulationRequest(
        product_id="prod-005",
        current_shelf_tier="EYE_LEVEL",
        target_shelf_tier="EYE_LEVEL",
        current_facing_count=1,
        target_facing_count=3,
        current_attractiveness_score=60.0,
        current_intrinsic_score=60.0,
    )
    result = PlanogramSimulator.simulate(req)

    assert result.facing_change == 2
    assert result.simulated_attractiveness_score >= result.original_attractiveness_score
    print(f"✓ Facing increase: change={result.facing_change}, "
          f"score {result.original_attractiveness_score} → {result.simulated_attractiveness_score}")


def test_simulator_serialization():
    """Result to_dict should produce valid JSON-serializable dict."""
    req = PlanogramSimulationRequest(
        product_id="prod-006",
        current_shelf_tier="TOUCH",
        target_shelf_tier="EYE_LEVEL",
        current_facing_count=2,
        target_facing_count=2,
        current_attractiveness_score=50.0,
        current_intrinsic_score=65.0,
    )
    result = PlanogramSimulator.simulate(req)
    d = result.to_dict()

    assert isinstance(d, dict)
    assert "product_id" in d
    assert "attention_lift_pct" in d
    assert "is_improvement" in d
    print(f"✓ Serialization OK: {len(d)} keys")


# ── Shelf Rules Tests ────────────────────────────────────────────

from app.modules.recommendation.shelf_rules import evaluate_shelf_rules


def test_shelf_hidden_gem_detection():
    """Products with high intrinsic on bottom tier should be flagged."""
    profiles = [{
        "product_id": "gem-001",
        "product_name": "Premium Organic Jam",
        "intrinsic_attractiveness_score": 82.0,
        "attractiveness_score": 35.0,
        "shelf_visibility": {
            "shelf_tier": "BOTTOM",
            "gamma_coefficient": 0.40,
        },
        "pillar_scores": {"interaction_score": 0.5},
    }]
    recs = evaluate_shelf_rules(profiles)
    assert len(recs) >= 1
    assert recs[0].category == RecommendationCategory.SHELF_OPTIMIZATION
    assert "Eye-Level" in recs[0].title
    print(f"✓ Hidden Gem detected: '{recs[0].title}'")


def test_shelf_squatter_detection():
    """Low-intrinsic eye-level products should be flagged for demotion."""
    profiles = [{
        "product_id": "squat-001",
        "product_name": "Generic Brand Soda",
        "intrinsic_attractiveness_score": 28.0,
        "attractiveness_score": 28.0,
        "shelf_visibility": {
            "shelf_tier": "EYE_LEVEL",
            "gamma_coefficient": 1.00,
        },
        "pillar_scores": {"interaction_score": 0.15},
    }]
    recs = evaluate_shelf_rules(profiles)
    assert len(recs) >= 1
    assert "Demote" in recs[0].title
    print(f"✓ Shelf Squatter detected: '{recs[0].title}'")


# ── Friction Rules Tests ─────────────────────────────────────────

from app.modules.recommendation.friction_rules import evaluate_friction_rules


def test_friction_high_dwell_low_pickup():
    """High dwell + low pickup should flag hesitation friction."""
    profiles = [{
        "product_id": "fric-001",
        "product_name": "Artisan Cheese Block",
        "total_viewers": 30,
        "average_attention_duration_sec": 8.5,
        "total_pickups": 2,
        "total_returns": 0,
        "total_purchases": 1,
        "intrinsic_attractiveness_score": 60.0,
    }]
    recs = evaluate_friction_rules(profiles)
    hesitation_recs = [r for r in recs if "Hesitation" in r.title]
    assert len(hesitation_recs) >= 1
    assert hesitation_recs[0].category == RecommendationCategory.CONSUMER_ENGAGEMENT
    print(f"✓ Hesitation friction: '{hesitation_recs[0].title}'")


def test_friction_high_pickup_high_return():
    """High pickup + high return should flag tactile mismatch."""
    profiles = [{
        "product_id": "fric-002",
        "product_name": "Premium Gift Set",
        "total_viewers": 20,
        "average_attention_duration_sec": 4.0,
        "total_pickups": 10,
        "total_returns": 8,
        "total_purchases": 2,
        "intrinsic_attractiveness_score": 55.0,
    }]
    recs = evaluate_friction_rules(profiles)
    return_recs = [r for r in recs if "Return" in r.title]
    assert len(return_recs) >= 1
    print(f"✓ Return friction: '{return_recs[0].title}'")


# ── Model Tests ──────────────────────────────────────────────────

def test_priority_from_impact():
    """Impact score should map to correct priority levels."""
    assert RecommendationPriority.from_impact_score(90) == RecommendationPriority.CRITICAL
    assert RecommendationPriority.from_impact_score(60) == RecommendationPriority.HIGH
    assert RecommendationPriority.from_impact_score(40) == RecommendationPriority.MEDIUM
    assert RecommendationPriority.from_impact_score(15) == RecommendationPriority.LOW
    print("✓ Priority mapping OK")


def test_expected_impact_composite():
    """Composite impact score should be weighted correctly."""
    impact = ExpectedImpact(attention_lift_pct=50.0, conversion_lift_pct=30.0)
    expected = 0.6 * 50.0 + 0.4 * 30.0  # 42.0
    assert abs(impact.composite_impact_score - expected) < 0.1
    print(f"✓ Composite impact: {impact.composite_impact_score} (expected ~{expected})")


def test_module9_summary_serialization():
    """Module9Summary should serialize to dict correctly."""
    summary = Module9Summary(
        total_recommendations=10,
        critical_count=2,
        high_count=3,
        medium_count=3,
        low_count=2,
    )
    d = summary.to_dict()
    assert d["total_recommendations"] == 10
    assert d["critical_count"] == 2
    assert "disclaimer" in d
    print(f"✓ Module9Summary serialization OK")


if __name__ == "__main__":
    tests = [
        test_simulator_bottom_to_eye_level,
        test_simulator_eye_level_to_bottom,
        test_simulator_same_tier_no_change,
        test_simulator_scores_bounded,
        test_simulator_facing_increase_lift,
        test_simulator_serialization,
        test_shelf_hidden_gem_detection,
        test_shelf_squatter_detection,
        test_friction_high_dwell_low_pickup,
        test_friction_high_pickup_high_return,
        test_priority_from_impact,
        test_expected_impact_composite,
        test_module9_summary_serialization,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"✗ {test.__name__}: {exc}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)
