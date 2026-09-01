"""
Module 9 — Consumer Engagement & Friction Rules
==================================================
Detects conversion bottlenecks across the 4-stage shopper journey:
  Passerby → Gaze Dwell → Pickup → Purchase

Generates targeted operational interventions for:
- High Dwell + Low Pickup (shopper hesitation / price confusion)
- High Pickup + High Return (tactile/expectation mismatch)
- Short Gaze / High Bounce (weak visual hook)
- Zero-Gaze Zone Calibration Alert (camera/shelf alignment)
"""

import uuid
from typing import Any, Dict, List

from app.modules.recommendation.models import (
    ActionableRecommendation,
    ExpectedImpact,
    RecommendationCategory,
    RecommendationPriority,
)


# ── Thresholds ────────────────────────────────────────────────
HIGH_DWELL_THRESHOLD = 5.0        # Seconds — above-average dwell
LOW_PICKUP_RATE_THRESHOLD = 0.15  # < 15% pickup rate
HIGH_PICKUP_RATE_THRESHOLD = 0.25 # > 25% pickup rate
HIGH_RETURN_RATE_THRESHOLD = 0.60 # > 60% return rate
SHORT_GAZE_THRESHOLD = 1.5        # Seconds — very short gaze
MIN_VIEWERS_FOR_ANALYSIS = 2      # Lowered to 2 for smaller test datasets


def evaluate_friction_rules(
    product_profiles: List[Dict[str, Any]],
) -> List[ActionableRecommendation]:
    """Evaluate shopper funnel friction points and generate interventions."""
    recommendations: List[ActionableRecommendation] = []

    total_store_passersby = sum(p.get("total_passersby", 0) for p in product_profiles)
    total_store_viewers = sum(p.get("total_viewers", 0) for p in product_profiles)

    # ── Zero-Gaze Zone / Camera Calibration Alert ─────────────────
    if len(product_profiles) > 0 and total_store_passersby >= 10 and total_store_viewers == 0:
        recommendations.append(ActionableRecommendation(
            id=f"friction-calib-{uuid.uuid4().hex[:8]}",
            category=RecommendationCategory.CONSUMER_ENGAGEMENT,
            priority=RecommendationPriority.HIGH,
            title="Verify Shelf ROI Calibration in Zone Annotator",
            description=(
                f"{total_store_passersby} shoppers were tracked in this camera zone, but 0 gaze "
                f"or pickup interactions mapped to the calibrated shelves. Camera alignment or "
                f"shelf polygon coordinates may require recalibration."
            ),
            target_type="ZONE",
            target_id="camera-zone-calibration",
            target_name="Shelf Calibration Layer",
            current_metrics={
                "total_tracked_shoppers": total_store_passersby,
                "shelf_viewers_detected": 0,
                "products_in_zone": len(product_profiles),
            },
            proposed_action=(
                "Open Zone Canvas Annotator in AI Analytics, verify shelf bounding boxes "
                "match physical fixture positions, and check camera tilt angle"
            ),
            expected_impact=ExpectedImpact(
                attention_lift_pct=50.0,
                conversion_lift_pct=20.0,
                confidence=0.90,
            ),
            rationale=(
                f"When pedestrian trajectories register foot traffic ({total_store_passersby} passersby) "
                f"but zero gaze rays intersect shelf polygons, it typically indicates bounding box drift "
                f"or uncalibrated camera homography rather than complete consumer disinterest."
            ),
        ))

    for profile in product_profiles:
        product_id = profile.get("product_id", "")
        product_name = profile.get("product_name", "Unknown Product")
        total_viewers = profile.get("total_viewers", 0)
        avg_attention = profile.get("average_attention_duration_sec", 0.0)
        total_pickups = profile.get("total_pickups", 0)
        total_returns = profile.get("total_returns", 0)
        total_purchases = profile.get("total_purchases", 0)

        # Skip products with insufficient data
        if total_viewers < MIN_VIEWERS_FOR_ANALYSIS:
            continue

        pickup_rate = total_pickups / max(1, total_viewers)
        return_rate = total_returns / max(1, total_pickups) if total_pickups > 0 else 0.0

        # ── High Dwell + Low Pickup (Shopper Hesitation) ─────────
        if avg_attention > HIGH_DWELL_THRESHOLD and pickup_rate < LOW_PICKUP_RATE_THRESHOLD:
            att_lift = round((avg_attention - HIGH_DWELL_THRESHOLD) * 5.0, 2)
            conv_lift = round(att_lift * 0.6, 2)

            recommendations.append(ActionableRecommendation(
                id=f"friction-hesitation-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.CONSUMER_ENGAGEMENT,
                priority=RecommendationPriority.HIGH,
                title=f"Reduce Shopper Hesitation for '{product_name}'",
                description=(
                    f"'{product_name}' attracts extended gaze dwell ({avg_attention:.1f}s) "
                    f"but has very low pickup rate ({pickup_rate:.1%}). Shoppers are "
                    f"interested but hesitating — likely price uncertainty or unclear specs."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "average_dwell_sec": round(avg_attention, 2),
                    "pickup_rate": round(pickup_rate, 4),
                    "total_viewers": total_viewers,
                    "total_pickups": total_pickups,
                    "funnel_stage": "GAZE_DWELL → PICKUP",
                },
                proposed_action=(
                    "Add prominent pricing labels, clear nutritional/ingredient badges, "
                    "comparison callouts, or benefit-focused shelf talkers"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=conv_lift,
                    confidence=min(1.0, max(0.4, total_viewers / 30.0)),
                ),
                rationale=(
                    f"Extended dwell time ({avg_attention:.1f}s) with low pickup rate ({pickup_rate:.1%}) "
                    f"indicates decision paralysis — the SKU draws attention but fails to convert."
                ),
            ))

        # ── High Pickup + High Return (Tactile/Expectation Mismatch) ──
        if (
            pickup_rate >= HIGH_PICKUP_RATE_THRESHOLD
            and return_rate >= HIGH_RETURN_RATE_THRESHOLD
            and total_pickups >= 2
        ):
            conv_lift = round(return_rate * 25.0, 2)

            recommendations.append(ActionableRecommendation(
                id=f"friction-return-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.CONSUMER_ENGAGEMENT,
                priority=RecommendationPriority.HIGH,
                title=f"Address Return Friction for '{product_name}'",
                description=(
                    f"'{product_name}' has high pickup rate ({pickup_rate:.1%}) but "
                    f"shoppers return it {return_rate:.1%} of the time without purchasing. "
                    f"Likely tactile disappointment or unexpected price on reverse."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "pickup_rate": round(pickup_rate, 4),
                    "return_rate": round(return_rate, 4),
                    "total_pickups": total_pickups,
                    "total_returns": total_returns,
                    "total_purchases": total_purchases,
                    "funnel_stage": "PICKUP → PURCHASE",
                },
                proposed_action=(
                    "Review packaging tactile quality, verify front-facing price visibility, "
                    "or audit price-to-value proposition"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=5.0,
                    conversion_lift_pct=conv_lift,
                    confidence=min(1.0, max(0.4, total_pickups / 15.0)),
                ),
                rationale=(
                    f"High pickup rate ({pickup_rate:.1%}) shows strong initial interest, but "
                    f"the {return_rate:.1%} return rate reveals post-pickup dissonance."
                ),
            ))

        # ── Short Gaze / High Bounce (Weak Visual Hook) ──────────
        if avg_attention < SHORT_GAZE_THRESHOLD and total_viewers >= 5:
            intrinsic = profile.get("intrinsic_attractiveness_score", 0.0)
            att_lift = round((SHORT_GAZE_THRESHOLD - avg_attention) * 15.0, 2)

            recommendations.append(ActionableRecommendation(
                id=f"friction-bounce-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.CONSUMER_ENGAGEMENT,
                priority=RecommendationPriority.MEDIUM,
                title=f"Improve Visual Hook for '{product_name}'",
                description=(
                    f"'{product_name}' receives very short gaze attention ({avg_attention:.1f}s "
                    f"avg) across {total_viewers} viewers. Packaging or shelf contrast may "
                    f"be insufficient to capture sustained attention."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "average_dwell_sec": round(avg_attention, 2),
                    "total_viewers": total_viewers,
                    "intrinsic_attractiveness": round(intrinsic, 2),
                },
                proposed_action=(
                    "Improve packaging contrast, adjust shelf lighting angle, "
                    "or reposition against less visually competing neighbors"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=round(att_lift * 0.2, 2),
                    confidence=min(1.0, max(0.4, total_viewers / 25.0)),
                ),
                rationale=(
                    f"Sub-{SHORT_GAZE_THRESHOLD}s average gaze ({avg_attention:.1f}s) "
                    f"indicates the product fails to capture visual attention despite "
                    f"exposure opportunities."
                ),
            ))

    return recommendations
