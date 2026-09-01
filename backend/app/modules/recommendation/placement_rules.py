"""
Module 9 — Product Placement Rules
=====================================
Evaluates intra-category pairwise planogram swaps and
cross-category co-merchandising affinity from co-interaction signals.
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
SWAP_INTRINSIC_GAP_THRESHOLD = 20.0   # Min gap between swap candidates
CO_INTERACTION_THRESHOLD = 3           # Min co-interactions for affinity


def evaluate_placement_rules(
    product_profiles: List[Dict[str, Any]],
) -> List[ActionableRecommendation]:
    """Evaluate pairwise swap opportunities and co-merchandising affinities."""
    recommendations: List[ActionableRecommendation] = []

    # Group products by category for intra-category swap analysis
    category_groups: Dict[str, List[Dict[str, Any]]] = {}
    for profile in product_profiles:
        cat = profile.get("category") or "Uncategorized"
        category_groups.setdefault(cat, []).append(profile)

    # ── Intra-Category Pairwise Swaps ────────────────────────────
    for category, products in category_groups.items():
        if len(products) < 2:
            continue

        # Find eye-level underperformers and bottom-tier overperformers
        eye_level_products = [
            p for p in products
            if p.get("shelf_visibility", {}).get("shelf_tier") == "EYE_LEVEL"
        ]
        lower_tier_products = [
            p for p in products
            if p.get("shelf_visibility", {}).get("shelf_tier") in ("BOTTOM", "TOUCH", "TOP")
        ]

        for eye_prod in eye_level_products:
            eye_intrinsic = eye_prod.get("intrinsic_attractiveness_score", 0.0)
            for lower_prod in lower_tier_products:
                lower_intrinsic = lower_prod.get("intrinsic_attractiveness_score", 0.0)

                gap = lower_intrinsic - eye_intrinsic
                if gap >= SWAP_INTRINSIC_GAP_THRESHOLD:
                    att_lift = round(gap * 0.4, 2)
                    conv_lift = round(att_lift * 0.3, 2)

                    eye_name = eye_prod.get("product_name", "Unknown")
                    lower_name = lower_prod.get("product_name", "Unknown")
                    lower_tier = lower_prod.get("shelf_visibility", {}).get("shelf_tier", "LOWER")

                    recommendations.append(ActionableRecommendation(
                        id=f"swap-{uuid.uuid4().hex[:8]}",
                        category=RecommendationCategory.PRODUCT_PLACEMENT,
                        priority=RecommendationPriority.HIGH if gap >= 30 else RecommendationPriority.MEDIUM,
                        title=f"Swap '{lower_name}' ↔ '{eye_name}'",
                        description=(
                            f"'{lower_name}' (intrinsic: {lower_intrinsic:.1f}, tier: {lower_tier}) "
                            f"outperforms '{eye_name}' (intrinsic: {eye_intrinsic:.1f}, eye-level) "
                            f"by {gap:.1f} points. Swapping positions could lift category attention."
                        ),
                        target_type="SHELF",
                        target_id=eye_prod.get("shelf_id", ""),
                        target_name=f"{category} shelf",
                        current_metrics={
                            "eye_level_product": eye_name,
                            "eye_level_intrinsic": round(eye_intrinsic, 2),
                            "swap_candidate": lower_name,
                            "swap_candidate_intrinsic": round(lower_intrinsic, 2),
                            "intrinsic_gap": round(gap, 2),
                        },
                        proposed_action=(
                            f"Swap shelf positions: move '{lower_name}' to Eye-Level, "
                            f"move '{eye_name}' to {lower_tier}"
                        ),
                        expected_impact=ExpectedImpact(
                            attention_lift_pct=att_lift,
                            conversion_lift_pct=conv_lift,
                            confidence=min(1.0, gap / 50.0),
                        ),
                        rationale=(
                            f"Intrinsic attractiveness gap of {gap:.1f} points between "
                            f"'{lower_name}' and '{eye_name}' within '{category}' category "
                            f"indicates sub-optimal shelf allocation. The higher-performing "
                            f"product should occupy the premium eye-level position."
                        ),
                        shelf_swap_details={
                            "product_a_id": eye_prod.get("product_id"),
                            "product_a_name": eye_name,
                            "product_a_from_tier": "EYE_LEVEL",
                            "product_a_to_tier": lower_tier,
                            "product_b_id": lower_prod.get("product_id"),
                            "product_b_name": lower_name,
                            "product_b_from_tier": lower_tier,
                            "product_b_to_tier": "EYE_LEVEL",
                        },
                    ))

    # ── Cross-Category Co-Merchandising Affinity ─────────────────
    # Detect products with high co-interaction signals
    for i, prod_a in enumerate(product_profiles):
        co_interactions = prod_a.get("co_interactions", {})
        for prod_b_id, count in co_interactions.items():
            if count >= CO_INTERACTION_THRESHOLD:
                # Find the corresponding product profile
                prod_b = next(
                    (p for p in product_profiles if p.get("product_id") == prod_b_id),
                    None,
                )
                if not prod_b:
                    continue

                a_name = prod_a.get("product_name", "Unknown")
                b_name = prod_b.get("product_name", "Unknown")

                # Only generate once per pair (avoid duplicates)
                if prod_a.get("product_id", "") > prod_b_id:
                    continue

                recommendations.append(ActionableRecommendation(
                    id=f"co-merch-{uuid.uuid4().hex[:8]}",
                    category=RecommendationCategory.PRODUCT_PLACEMENT,
                    priority=RecommendationPriority.LOW,
                    title=f"Co-merchandise '{a_name}' + '{b_name}'",
                    description=(
                        f"Shoppers frequently interact with both '{a_name}' and '{b_name}' "
                        f"in the same session ({count} co-interactions detected). "
                        f"Placing them adjacent could increase basket size."
                    ),
                    target_type="PRODUCT",
                    target_id=prod_a.get("product_id", ""),
                    target_name=a_name,
                    current_metrics={
                        "co_interaction_count": count,
                        "product_a": a_name,
                        "product_b": b_name,
                    },
                    proposed_action=f"Place '{a_name}' and '{b_name}' on adjacent shelf facings or shared endcap",
                    expected_impact=ExpectedImpact(
                        attention_lift_pct=round(count * 2.0, 2),
                        conversion_lift_pct=round(count * 1.5, 2),
                        confidence=min(1.0, count / 10.0),
                    ),
                    rationale=(
                        f"Cross-interaction telemetry shows {count} shoppers engaged with "
                        f"both products in the same visit, indicating complementary appeal."
                    ),
                ))

    return recommendations
