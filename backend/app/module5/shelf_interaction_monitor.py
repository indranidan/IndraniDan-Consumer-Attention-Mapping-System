"""
Module 5 — Shelf Interaction Monitor & Product Engagement Aggregator
======================================================================
Monitors and aggregates shopper-shelf and shopper-product interactions.
Strictly separates:
- SHELF VISIT (presence in shelf zone)
- SHELF ATTENTION (head pose / gaze focused on shelf)
- SHELF INTERACTION (dwell + proximity + attention at shelf)
- PRODUCT INTERACTION (product-level views, pickups, returns, comparisons)
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from app.module5.models import (
    InteractionEventType,
    ProductEngagementMetric,
    ProductInteractionEvent,
    ShelfInteractionMetric,
)


class Module5ShelfInteractionMonitor:
    """
    Computes shelf interaction metrics and structured product engagement records.
    """

    def compute_shelf_interactions(
        self,
        events: List[ProductInteractionEvent],
        configured_shelves: List[Dict[str, Any]],
        zone_visits: List[Dict[str, Any]],
        zone_dwell_map: Dict[str, float],
        zone_visitor_map: Dict[str, int],
        products_by_shelf: Dict[str, List[Dict[str, Any]]],
    ) -> List[ShelfInteractionMetric]:
        """
        Calculate per-shelf metrics strictly distinguishing visits, attention, and interactions.
        """
        metrics: List[ShelfInteractionMetric] = []

        for sh in configured_shelves:
            sh_id = str(sh.get("id") or sh.get("shelf_code") or sh.get("shelf_id") or "")
            sh_name = str(sh.get("name") or sh.get("shelf_name") or f"Shelf {sh_id}")
            sh_code = sh.get("shelf_code")
            zone_id = str(sh.get("zone_id") or sh_id)

            # 1. Shelf Visits (from Zone visit records / dwell)
            visits_count = zone_visitor_map.get(zone_id, 0)
            if visits_count == 0 and zone_id in zone_dwell_map:
                visits_count = 1 if zone_dwell_map[zone_id] > 0 else 0

            # Also check direct zone visit objects
            zone_v_matches = [
                zv for zv in zone_visits
                if str(zv.get("zone_id", "")) == zone_id or str(zv.get("zone_name", "")).lower() == sh_name.lower()
            ]
            if zone_v_matches:
                unique_track_visitors = {int(zv.get("tracking_id", 0)) for zv in zone_v_matches if int(zv.get("tracking_id", 0)) > 0}
                visits_count = max(visits_count, len(unique_track_visitors), len(zone_v_matches))

            # 2. Shelf Attention Events & Viewers (from interaction/attention events)
            shelf_events = [
                e for e in events
                if (e.shelf_id and (e.shelf_id == sh_id or e.shelf_id == sh_code))
                or (e.shelf_name and e.shelf_name.lower() == sh_name.lower())
            ]

            view_events = [e for e in shelf_events if e.event_type == InteractionEventType.PRODUCT_VIEWED]
            pickup_events = [e for e in shelf_events if e.event_type == InteractionEventType.PRODUCT_PICKED_UP]
            return_events = [e for e in shelf_events if e.event_type == InteractionEventType.PRODUCT_RETURNED]

            unique_viewers = len({e.track_id for e in view_events})
            shelf_attention_time = sum(e.duration_seconds for e in view_events)
            shelf_attn_count = len(view_events)

            # 3. Shelf Interactions (Interactions where duration >= 1.0s or physical touch / comparison occurred)
            sustained_interactions = [e for e in shelf_events if e.duration_seconds >= 1.0 or e.event_type in (InteractionEventType.PRODUCT_PICKED_UP, InteractionEventType.PRODUCT_RETURNED)]
            shelf_interactions_count = len(sustained_interactions)

            total_engagement_dur = sum(e.duration_seconds for e in shelf_events)
            avg_engagement_dur = (total_engagement_dur / len(shelf_events)) if shelf_events else 0.0

            assigned_prods = products_by_shelf.get(sh_id, []) or products_by_shelf.get(sh_code, [])

            metric = ShelfInteractionMetric(
                shelf_id=sh_id,
                shelf_name=sh_name,
                shelf_code=sh_code,
                zone_id=zone_id,
                shelf_visits=visits_count,
                shelf_viewers=unique_viewers,
                shelf_attention_events=shelf_attn_count,
                shelf_attention_duration_sec=shelf_attention_time,
                product_views=len(view_events),
                shelf_interactions=shelf_interactions_count,
                pickup_events=len(pickup_events),
                return_events=len(return_events),
                total_engagement_duration_sec=total_engagement_dur,
                average_engagement_duration_sec=avg_engagement_dur,
                associated_products_count=len(assigned_prods),
            )
            metrics.append(metric)

        return metrics

    def compute_product_engagement(
        self,
        events: List[ProductInteractionEvent],
        all_products: List[Dict[str, Any]],
        comparison_events: List[ProductInteractionEvent],
        is_spatial_mapped: bool = False,
    ) -> List[ProductEngagementMetric]:
        """
        Compute structured engagement metrics for each configured product.
        """
        product_metrics: List[ProductEngagementMetric] = []

        for p in all_products:
            p_id = str(p.get("id") or p.get("product_id") or "")
            p_name = str(p.get("name") or p.get("product_name") or "Unknown Product")
            p_sku = p.get("sku")
            shelf_id = str(p.get("shelf_id") or "")
            shelf_name = p.get("shelf_name")

            # Match events for this product (by product_id or by shelf_id if shelf-associated)
            matched_events = [
                e for e in events
                if (e.product_id and e.product_id == p_id)
                or (not e.product_id and e.shelf_id and e.shelf_id == shelf_id)
            ]

            view_events = [e for e in matched_events if e.event_type == InteractionEventType.PRODUCT_VIEWED]
            pickup_events = [e for e in matched_events if e.event_type == InteractionEventType.PRODUCT_PICKED_UP]
            return_events = [e for e in matched_events if e.event_type == InteractionEventType.PRODUCT_RETURNED]
            purchase_events = [e for e in matched_events if e.event_type == InteractionEventType.PRODUCT_PURCHASED]

            # Comparisons involving this product
            comp_count = sum(
                1 for ce in comparison_events
                if p_name in (ce.product_name or "") or p_id in (ce.metadata.get("items_compared", []))
            )

            # Repeat interactions: shoppers who viewed/interacted > 1 time
            shopper_view_counts: Dict[int, int] = {}
            for e in view_events:
                shopper_view_counts[e.track_id] = shopper_view_counts.get(e.track_id, 0) + 1
            repeat_count = sum(1 for cnt in shopper_view_counts.values() if cnt > 1)

            unique_viewers = len(shopper_view_counts)
            total_view_duration = sum(e.duration_seconds for e in view_events)
            avg_view_duration = (total_view_duration / len(view_events)) if view_events else 0.0

            status_note = "Active (Direct Spatial Polygon)" if is_spatial_mapped else "Active (Mapped via Shelf Association)"

            metric = ProductEngagementMetric(
                product_id=p_id,
                product_name=p_name,
                sku=p_sku,
                shelf_id=shelf_id,
                shelf_name=shelf_name,
                is_spatial_mapped=is_spatial_mapped,
                views=len(view_events),
                unique_viewers=unique_viewers,
                total_view_duration_sec=total_view_duration,
                average_view_duration_sec=avg_view_duration,
                pickup_events=len(pickup_events),
                return_events=len(return_events),
                comparison_events=comp_count,
                repeat_interactions=repeat_count,
                purchase_count=len(purchase_events),
                status_note=status_note,
            )
            product_metrics.append(metric)

        return product_metrics
