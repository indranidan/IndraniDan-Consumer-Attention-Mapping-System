"""
Module 9 — Store Layout & Traffic Flow Rules
===============================================
Uses Module 7 heatmaps and Module 6 behavior data to suggest:
- Dead zone / cold spot activation with anchor SKUs
- Aisle congestion mitigation and fixture spacing adjustments
- Archetype-tailored layout modifications
"""

import uuid
from typing import Any, Dict, List, Optional

from app.modules.recommendation.models import (
    ActionableRecommendation,
    ExpectedImpact,
    RecommendationCategory,
    RecommendationPriority,
)


# ── Thresholds ────────────────────────────────────────────────
DEAD_ZONE_DWELL_PERCENTILE = 0.15     # Bottom 15th percentile
CONGESTION_DENSITY_THRESHOLD = 0.80   # Top 80th percentile density
MIN_ZONES_FOR_ANALYSIS = 2


def evaluate_layout_rules(
    product_profiles: List[Dict[str, Any]],
    heatmap_data: Optional[Dict[str, Any]] = None,
    behavior_data: Optional[Dict[str, Any]] = None,
) -> List[ActionableRecommendation]:
    """Evaluate store layout and traffic flow improvement opportunities."""
    recommendations: List[ActionableRecommendation] = []

    # ── Dead Zone / Cold Spot Activation ─────────────────────────
    if heatmap_data:
        zones = heatmap_data.get("zones", [])
        if len(zones) >= MIN_ZONES_FOR_ANALYSIS:
            # Calculate dwell time percentiles
            dwell_times = [z.get("dwell_time", 0.0) for z in zones]
            dwell_times_sorted = sorted(dwell_times)
            percentile_15_idx = max(0, int(len(dwell_times_sorted) * DEAD_ZONE_DWELL_PERCENTILE))
            dwell_threshold = dwell_times_sorted[percentile_15_idx] if dwell_times_sorted else 0.0

            # Identify top-performing anchor products for relocation suggestions
            anchor_candidates = sorted(
                product_profiles,
                key=lambda p: p.get("attractiveness_score", 0.0),
                reverse=True,
            )[:3]
            anchor_names = [p.get("product_name", "Popular Item") for p in anchor_candidates]

            for zone in zones:
                zone_dwell = zone.get("dwell_time", 0.0)
                zone_name = zone.get("zone_name", zone.get("name", "Unknown Zone"))
                zone_id = zone.get("zone_id", zone.get("id", ""))
                zone_density = zone.get("density", zone.get("traffic_density", 0.0))

                # Dead zone detection
                if zone_dwell <= dwell_threshold and zone_dwell >= 0:
                    recommendations.append(ActionableRecommendation(
                        id=f"layout-deadzone-{uuid.uuid4().hex[:8]}",
                        category=RecommendationCategory.LAYOUT_IMPROVEMENT,
                        priority=RecommendationPriority.HIGH,
                        title=f"Activate Dead Zone: '{zone_name}'",
                        description=(
                            f"Zone '{zone_name}' has dwell time ({zone_dwell:.1f}s) in the "
                            f"bottom 15th percentile. Placing anchor destination products or "
                            f"directional signage could pull traffic through this zone."
                        ),
                        target_type="ZONE",
                        target_id=str(zone_id),
                        target_name=zone_name,
                        current_metrics={
                            "dwell_time": round(zone_dwell, 2),
                            "dwell_threshold_15pct": round(dwell_threshold, 2),
                            "traffic_density": round(zone_density, 4) if zone_density else None,
                        },
                        proposed_action=(
                            f"Place high-draw anchor SKUs (e.g., {', '.join(anchor_names[:2])}) "
                            f"in this zone or add directional wayfinding signage to drive footfall"
                        ),
                        expected_impact=ExpectedImpact(
                            attention_lift_pct=25.0,
                            conversion_lift_pct=10.0,
                            confidence=0.55,
                        ),
                        rationale=(
                            f"Zone '{zone_name}' registers minimal shopper engagement. "
                            f"Destination/anchor product placement is a proven strategy "
                            f"to redistribute foot traffic across underutilized retail space."
                        ),
                    ))

                # Congestion detection
                if zone_density and zone_density >= CONGESTION_DENSITY_THRESHOLD:
                    recommendations.append(ActionableRecommendation(
                        id=f"layout-congestion-{uuid.uuid4().hex[:8]}",
                        category=RecommendationCategory.LAYOUT_IMPROVEMENT,
                        priority=RecommendationPriority.MEDIUM,
                        title=f"Reduce Congestion in '{zone_name}'",
                        description=(
                            f"Zone '{zone_name}' has high traffic density ({zone_density:.2f}) "
                            f"indicating potential aisle congestion and velocity drops. "
                            f"Fixture spacing or product dispersion may be needed."
                        ),
                        target_type="ZONE",
                        target_id=str(zone_id),
                        target_name=zone_name,
                        current_metrics={
                            "traffic_density": round(zone_density, 4),
                            "dwell_time": round(zone_dwell, 2),
                        },
                        proposed_action=(
                            "Widen aisle clearance, reposition promotional floor displays, "
                            "or disperse clustered top-selling items across adjacent zones"
                        ),
                        expected_impact=ExpectedImpact(
                            attention_lift_pct=10.0,
                            conversion_lift_pct=8.0,
                            confidence=0.50,
                        ),
                        rationale=(
                            f"High traffic density ({zone_density:.2f}) suggests shoppers "
                            f"bottleneck in this area. Explorer and Quick Buyer trajectory "
                            f"congestion reduces browsing comfort and dwell quality."
                        ),
                    ))

    # ── Behavior-Based Layout Suggestions ────────────────────────
    if behavior_data:
        archetypes = behavior_data.get("archetypes", {})
        explorer_pct = archetypes.get("Explorer", 0.0)
        quick_buyer_pct = archetypes.get("Quick Buyer", 0.0)

        if explorer_pct >= 0.30:
            recommendations.append(ActionableRecommendation(
                id=f"layout-explorer-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.LAYOUT_IMPROVEMENT,
                priority=RecommendationPriority.LOW,
                title="Create Discovery Zone for Explorer Shoppers",
                description=(
                    f"Explorer shoppers represent {explorer_pct:.0%} of detected visitors. "
                    f"Dedicate a zone with interactive displays, product sampling, or "
                    f"curated discovery shelves to serve this segment."
                ),
                target_type="STORE",
                target_id="store-layout",
                target_name="Store Layout",
                current_metrics={
                    "explorer_percentage": round(explorer_pct, 4),
                },
                proposed_action=(
                    "Designate a discovery/exploration hub with product sampling stations, "
                    "interactive displays, and new-arrival featured shelves"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=15.0,
                    conversion_lift_pct=8.0,
                    confidence=0.45,
                ),
                rationale=(
                    f"A significant {explorer_pct:.0%} Explorer segment suggests the store "
                    f"serves a browsing-heavy clientele. Dedicated discovery zones increase "
                    f"engagement depth and basket size for this archetype."
                ),
            ))

        if quick_buyer_pct >= 0.25:
            recommendations.append(ActionableRecommendation(
                id=f"layout-quickbuy-{uuid.uuid4().hex[:8]}",
                category=RecommendationCategory.LAYOUT_IMPROVEMENT,
                priority=RecommendationPriority.LOW,
                title="Add Express Navigation for Quick Buyers",
                description=(
                    f"Quick Buyer shoppers represent {quick_buyer_pct:.0%} of visitors. "
                    f"Clear category signage, express checkout lanes, and grab-and-go "
                    f"zones would improve their experience."
                ),
                target_type="STORE",
                target_id="store-layout",
                target_name="Store Layout",
                current_metrics={
                    "quick_buyer_percentage": round(quick_buyer_pct, 4),
                },
                proposed_action=(
                    "Deploy clear category wayfinding signage, create grab-and-go zones "
                    "near store entrance, and establish express self-checkout lanes"
                ),
                expected_impact=ExpectedImpact(
                    attention_lift_pct=8.0,
                    conversion_lift_pct=12.0,
                    confidence=0.45,
                ),
                rationale=(
                    f"Quick Buyers ({quick_buyer_pct:.0%}) prioritize speed and efficiency. "
                    f"Removing navigation friction increases their purchase completion rate "
                    f"and overall satisfaction."
                ),
            ))

    return recommendations
