"""
Module 9 — Shelf Optimization Rules
======================================
Evaluates intrinsic vs. observed attractiveness gap to generate:
- "Hidden Gem" tier promotion recommendations (bottom/reach → eye-level)
- "Shelf Squatter" demotion recommendations (eye-level underperformers)
- Category-level planogram and facing rebalancing suggestions
- Tier auto-inference for UNKNOWN shelves
"""

import uuid
from typing import Any, Dict, List, Optional

from app.modules.recommendation.models import (
    ActionableRecommendation,
    ExpectedImpact,
    RecommendationCategory,
    RecommendationPriority,
)
from app.modules.scoring.models import SHELF_TIER_GAMMA, ShelfTier


# ── Thresholds ────────────────────────────────────────────────
HIDDEN_GEM_INTRINSIC_THRESHOLD = 65.0     # Min intrinsic score for promotion
HIDDEN_GEM_GAMMA_THRESHOLD = 0.85         # Max current gamma for promotion
SQUATTER_INTRINSIC_THRESHOLD = 45.0       # Max intrinsic score for squatters
EYE_LEVEL_GAMMA = 1.00


def infer_shelf_tier(
    tier_str: Optional[str] = None,
    shelf_name: Optional[str] = None,
    shelf_code: Optional[str] = None,
) -> ShelfTier:
    """Intelligently infer shelf tier from string or metadata keywords."""
    if tier_str and tier_str != "UNKNOWN":
        tier_map = {
            "EYE_LEVEL": ShelfTier.EYE_LEVEL,
            "TOP": ShelfTier.TOP,
            "TOUCH": ShelfTier.TOUCH,
            "BOTTOM": ShelfTier.BOTTOM,
        }
        if tier_str.upper() in tier_map:
            return tier_map[tier_str.upper()]

    # Infer from shelf_name or shelf_code keywords
    text = f"{shelf_name or ''} {shelf_code or ''}".lower()
    if any(k in text for k in ["eye", "hero", "center", "focal"]):
        return ShelfTier.EYE_LEVEL
    elif any(k in text for k in ["top", "stretch", "upper", "high"]):
        return ShelfTier.TOP
    elif any(k in text for k in ["touch", "chest", "mid", "middle", "reach"]):
        return ShelfTier.TOUCH
    elif any(k in text for k in ["bottom", "stoop", "floor", "lower", "base"]):
        return ShelfTier.BOTTOM

    return ShelfTier.UNKNOWN


def _get_gamma(tier: ShelfTier) -> float:
    """Resolve gamma coefficient from ShelfTier enum."""
    return SHELF_TIER_GAMMA.get(tier, 0.75)


def _compute_attention_lift(current_gamma: float, target_gamma: float, intrinsic_score: float) -> float:
    """Estimate attention lift percentage from tier change."""
    if current_gamma <= 0:
        return 0.0
    gamma_ratio = (target_gamma - current_gamma) / current_gamma
    return round(max(5.0, gamma_ratio * max(20.0, intrinsic_score) * 0.5), 2)


def evaluate_shelf_rules(product_profiles: List[Dict[str, Any]]) -> List[ActionableRecommendation]:
    """Evaluate shelf tier optimization rules across all scored products."""
    recommendations: List[ActionableRecommendation] = []

    # Category grouping for relative tier analysis
    category_groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in product_profiles:
        cat = p.get("category") or "General"
        category_groups.setdefault(cat, []).append(p)

    for profile in product_profiles:
        intrinsic = profile.get("intrinsic_attractiveness_score", 0.0)
        observed = profile.get("attractiveness_score", 0.0)
        shelf_vis = profile.get("shelf_visibility", {})
        raw_tier = shelf_vis.get("shelf_tier", "UNKNOWN")
        shelf_name = profile.get("shelf_name", "")
        product_id = profile.get("product_id", "")
        product_name = profile.get("product_name", "Unknown Product")
        interaction_score = profile.get("pillar_scores", {}).get("interaction_score", 0.0)

        # Infer tier if unknown
        tier = infer_shelf_tier(raw_tier, shelf_name=shelf_name)
        current_gamma = _get_gamma(tier)
        tier_str = tier.value

        # ── 1. Hidden Gem Detection ──────────────────────────────
        if intrinsic >= HIDDEN_GEM_INTRINSIC_THRESHOLD and current_gamma < HIDDEN_GEM_GAMMA_THRESHOLD:
            gap = intrinsic - observed
            att_lift = _compute_attention_lift(current_gamma, EYE_LEVEL_GAMMA, intrinsic)
            conv_lift = round(att_lift * 0.35, 2)

            priority = (
                RecommendationPriority.CRITICAL if gap >= 25.0
                else RecommendationPriority.HIGH
            )

            recommendations.append(ActionableRecommendation(
                id=f"shelf-gem-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.SHELF_OPTIMIZATION,
                priority=priority,
                title=f"Promote '{product_name}' to Eye-Level Tier",
                description=(
                    f"'{product_name}' has high intrinsic appeal ({intrinsic:.1f}) "
                    f"but is placed on {tier_str} tier (γ={current_gamma:.2f}). "
                    f"Moving to Eye-Level could increase attention by ~{att_lift:.1f}%."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "intrinsic_attractiveness": round(intrinsic, 2),
                    "observed_attractiveness": round(observed, 2),
                    "current_tier": tier_str,
                    "current_gamma": round(current_gamma, 2),
                    "gap": round(gap, 2),
                },
                proposed_action="Relocate to Eye-Level shelf tier (γ=1.00)",
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_lift,
                    conversion_lift_pct=conv_lift,
                    confidence=min(1.0, intrinsic / 100.0),
                ),
                rationale=(
                    f"High intrinsic appeal ({intrinsic:.1f}) is constrained by current shelf "
                    f"visibility ({tier_str}, γ={current_gamma:.2f}). Promoting to eye-level "
                    f"will unlock significant attention yield."
                ),
                shelf_swap_details={
                    "from_tier": tier_str,
                    "to_tier": "EYE_LEVEL",
                    "from_gamma": current_gamma,
                    "to_gamma": EYE_LEVEL_GAMMA,
                },
            ))

        # ── 2. Shelf Squatter Detection ──────────────────────────
        elif (
            tier == ShelfTier.EYE_LEVEL
            and intrinsic < SQUATTER_INTRINSIC_THRESHOLD
            and interaction_score < 0.3
        ):
            att_loss = round(abs(intrinsic - 50.0) * 0.3, 2)

            recommendations.append(ActionableRecommendation(
                id=f"shelf-squat-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.SHELF_OPTIMIZATION,
                priority=RecommendationPriority.MEDIUM,
                title=f"Demote '{product_name}' from Eye-Level",
                description=(
                    f"'{product_name}' occupies premium Eye-Level space but has low "
                    f"intrinsic attractiveness ({intrinsic:.1f}) and weak interaction yield "
                    f"({interaction_score:.2f}). Reallocating to touch/bottom tier."
                ),
                target_type="PRODUCT",
                target_id=product_id,
                target_name=product_name,
                current_metrics={
                    "intrinsic_attractiveness": round(intrinsic, 2),
                    "interaction_score": round(interaction_score, 4),
                    "current_tier": tier_str,
                },
                proposed_action="Demote to Touch or Bottom tier; reduce facing count",
                expected_impact=ExpectedImpact(
                    attention_lift_pct=att_loss,
                    conversion_lift_pct=round(att_loss * 0.2, 2),
                    confidence=0.6,
                ),
                rationale=(
                    f"Low appeal ({intrinsic:.1f}) underutilizes premium eye-level real estate. "
                    f"Relocating liberates high-traffic shelf space for top-performing SKUs."
                ),
                shelf_swap_details={
                    "from_tier": "EYE_LEVEL",
                    "to_tier": "TOUCH",
                    "from_gamma": EYE_LEVEL_GAMMA,
                    "to_gamma": SHELF_TIER_GAMMA.get(ShelfTier.TOUCH, 0.85),
                },
            ))

    # ── 3. Category-Level Planogram Rebalancing for UNKNOWN Tiers ──
    for category, products in category_groups.items():
        if len(products) >= 2:
            sorted_prods = sorted(products, key=lambda p: p.get("attractiveness_score", 0.0), reverse=True)
            top_p = sorted_prods[0]
            bottom_p = sorted_prods[-1]
            top_score = top_p.get("attractiveness_score", 0.0)
            bottom_score = bottom_p.get("attractiveness_score", 0.0)

            # Check if all products have UNKNOWN tier and there's a score differential
            all_unknown = all(
                infer_shelf_tier(p.get("shelf_visibility", {}).get("shelf_tier")) == ShelfTier.UNKNOWN
                for p in products
            )

            if all_unknown and (top_score - bottom_score >= 10.0):
                top_name = top_p.get("product_name", "Top Product")
                bottom_name = bottom_p.get("product_name", "Lower Product")
                diff = round(top_score - bottom_score, 1)

                recommendations.append(ActionableRecommendation(
                    id=f"shelf-cat-rebalance-{uuid.uuid4().hex[:8]}",
                    category=RecommendationCategory.SHELF_OPTIMIZATION,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Rebalance Facings in '{category}' Category",
                    description=(
                        f"In category '{category}', '{top_name}' ({top_score:.1f}) outperforms "
                        f"'{bottom_name}' ({bottom_score:.1f}) by {diff} points. "
                        f"Assign vertical shelf tiers and give extra facings to '{top_name}'."
                    ),
                    target_type="SHELF",
                    target_id=top_p.get("shelf_id") or category,
                    target_name=f"{category} Fixture",
                    current_metrics={
                        "category": category,
                        "top_performer": top_name,
                        "top_score": top_score,
                        "bottom_performer": bottom_name,
                        "bottom_score": bottom_score,
                        "score_gap": diff,
                    },
                    proposed_action=(
                        f"Assign '{top_name}' to eye-level with +1 facing; "
                        f"reduce facings for '{bottom_name}'"
                    ),
                    expected_impact=ExpectedImpact(
                        attention_lift_pct=round(diff * 0.4, 2),
                        conversion_lift_pct=round(diff * 0.15, 2),
                        confidence=0.55,
                    ),
                    rationale=(
                        f"Merchandising facing reallocation in '{category}' shifts visual focus "
                        f"to top-performing SKUs, maximizing basket conversion yield."
                    ),
                ))

    return recommendations
