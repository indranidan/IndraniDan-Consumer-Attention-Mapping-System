"""
Module 9 — Promotional Placement Rules
=========================================
Identifies SKUs for promotional amplification:
- High-conversion endcap and promotional island nominations
- Low-gaze / high-traffic shelf talker and signage callouts
- Foot-traffic exposure recovery for zero-gaze high-passerby products
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
ENDCAP_CONVERSION_THRESHOLD = 65.0       # Min conversion potential score
ENDCAP_MARKETING_THRESHOLD = 60.0        # Min marketing effectiveness score
LOW_GAZE_VIEW_RATE_THRESHOLD = 0.15      # Max view rate (viewers / passersby)
HIGH_TRAFFIC_PASSERSBY_THRESHOLD = 15    # Min passersby count for high-traffic


def evaluate_promo_rules(
    product_profiles: List[Dict[str, Any]],
) -> List[ActionableRecommendation]:
    """Evaluate promotional placement and signage rules."""
    recommendations: List[ActionableRecommendation] = []

    # Identify category top performers
    category_best: Dict[str, float] = {}
    for p in product_profiles:
        cat = p.get("category") or "General"
        score = p.get("attractiveness_score", 0.0)
        category_best[cat] = max(category_best.get(cat, 0.0), score)

    for profile in product_profiles:
        product_id = profile.get("product_id", "")
        product_name = profile.get("product_name", "Unknown Product")
        category = profile.get("category") or "General"
        attractiveness = profile.get("attractiveness_score", 0.0)
        conversion_potential = profile.get("conversion_potential_score", 0.0)
        marketing_effectiveness = profile.get("marketing_effectiveness_score", 0.0)
        total_viewers = profile.get("total_viewers", 0)
        total_passersby = profile.get("total_passersby", 0)
        pillar_scores = profile.get("pillar_scores", {})
        pickup_score = pillar_scores.get("pickup_score", 0.0)
        intrinsic = profile.get("intrinsic_attractiveness_score", 0.0)
        view_rate = total_viewers / max(1, total_passersby)

        # ── 1. Endcap / Promotional Island Nominations ───────────
        is_category_leader = attractiveness >= 60.0 and attractiveness >= category_best.get(cat, 0.0) - 1.0
        if (
            (conversion_potential >= ENDCAP_CONVERSION_THRESHOLD and marketing_effectiveness >= ENDCAP_MARKETING_THRESHOLD)
            or is_category_leader
        ) and total_passersby >= 5:
            att_lift = round(max(15.0, (conversion_potential + marketing_effectiveness) * 0.15), 2)
            conv_lift = round(att_lift * 0.45, 2)

            recommendations.append(ActionableRecommendation(
                id=f"promo-endcap-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.PROMOTIONAL_PLACEMENT,
                priority=RecommendationPriority.HIGH,
                title=f"Feature '{product_name}' on Promotional Endcap",
                description=(
                    f"'{product_name}' demonstrates strong performance metrics in '{category}' "
                    f"(Attractiveness: {attractiveness:.1f}, Conv Potential: {conversion_potential:.1f}). "
                    f"Ideal candidate for featured endcap or promotional display."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "category": category,
                    "attractiveness_score": round(attractiveness, 2),
                    "conversion_potential_score": round(conversion_potential, 2),
                    "marketing_effectiveness_score": round(marketing_effectiveness, 2),
                },
                proposed_action=(
                    "Feature on front-of-store endcap, seasonal promo island, "
                    "or checkout impulse zone display"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=conv_lift,
                    confidence=min(1.0, max(0.4, conversion_potential / 100.0)),
                ),
                rationale=(
                    f"Strong performance profile ({attractiveness:.1f}) in '{category}' indicates "
                    f"this SKU responds well to amplified visibility. Promotional placement would "
                    f"maximize return on prime retail display assets."
                ),
            ))

        # ── 2. High-Traffic / Zero-Gaze Exposure Fix ─────────────
        elif total_passersby >= HIGH_TRAFFIC_PASSERSBY_THRESHOLD and total_viewers == 0:
            att_lift = 35.0
            conv_lift = 12.0

            recommendations.append(ActionableRecommendation(
                id=f"promo-zerogaze-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.PROMOTIONAL_PLACEMENT,
                priority=RecommendationPriority.HIGH,
                title=f"Capture Missed Footfall for '{product_name}'",
                description=(
                    f"'{product_name}' received {total_passersby} passersby opportunities but "
                    f"captured 0 visual impressions. High foot-traffic is currently going unmonetized."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "total_passersby": total_passersby,
                    "total_viewers": 0,
                    "view_rate": "0.0%",
                    "category": category,
                },
                proposed_action=(
                    "Deploy high-contrast shelf talkers, promotional wobblers, "
                    "bright product backdrops, or dedicated shelf LED lighting"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=conv_lift,
                    confidence=0.70,
                ),
                rationale=(
                    f"Significant foot-traffic ({total_passersby} passersby) passed this SKU without "
                    f"looking. Visual disruption mechanisms (talkers/color accents) are necessary to "
                    f"break shopper visual autopilot."
                ),
            ))

        # ── 3. Low-Gaze / High-Traffic Shelf Talker Callouts ────
        elif (
            total_passersby >= HIGH_TRAFFIC_PASSERSBY_THRESHOLD
            and 0 < view_rate < LOW_GAZE_VIEW_RATE_THRESHOLD
        ):
            att_lift = round((1.0 - view_rate) * 25.0, 2)

            recommendations.append(ActionableRecommendation(
                id=f"promo-signage-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.PROMOTIONAL_PLACEMENT,
                priority=RecommendationPriority.MEDIUM,
                title=f"Add Shelf Signage for '{product_name}'",
                description=(
                    f"'{product_name}' receives high passerby traffic ({total_passersby}) "
                    f"but captures gaze from only {view_rate:.1%} of passersby. "
                    f"Visual signage could increase attention capture."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "total_passersby": total_passersby,
                    "total_viewers": total_viewers,
                    "view_rate": round(view_rate, 4),
                    "intrinsic_attractiveness": round(intrinsic, 2),
                },
                proposed_action=(
                    "Deploy shelf talkers, highlight key product benefits, "
                    "or adjust shelf facing orientation"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=round(att_lift * 0.25, 2),
                    confidence=0.65,
                ),
                rationale=(
                    f"High foot traffic ({total_passersby} passersby) but low gaze conversion "
                    f"({view_rate:.1%}) indicates the SKU needs increased visual salience."
                ),
            ))

    return recommendations
