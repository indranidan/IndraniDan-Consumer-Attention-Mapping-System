"""
Module 4 — Attention Metrics & Analytical Scoring
===================================================
Calculates separate, rigorous metrics:
1. Dwell Time (physical presence in zone, from Module 3)
2. View Duration (time spent looking at targets)
3. Shelf Attention Time (sustained attention toward shelf)
4. Product Focus Duration (sustained attention toward product, or N/A)
5. Repeated Attention Events (re-engagement count)
6. Shelf Engagement Score (clearly defined analytical metric)
"""

from typing import Dict, List, Optional
from app.modules.attention.models import (
    AttentionEventRecord,
    ProductAttention,
    ShelfEngagement,
)


def calculate_shelf_engagement_score(
    shelf_attention_time_sec: float,
    dwell_time_sec: float,
    repeated_events: int,
) -> float:
    """
    Compute analytical Shelf Engagement Score (0 - 100).

    Formula:
      - 40% Weight: Attention / Dwell Ratio (Gaze engagement relative to time spent in zone)
      - 35% Weight: Total Attention Duration (Normalized to 10.0 seconds benchmark)
      - 25% Weight: Repeated Attention Frequency (Normalized to 3.0 visits benchmark)

    Score is purely analytical and does NOT measure psychological purchase intent.
    """
    effective_dwell = max(dwell_time_sec, 1.0)
    ratio_term = min(1.0, shelf_attention_time_sec / effective_dwell)
    duration_term = min(1.0, shelf_attention_time_sec / 10.0)
    repeated_term = min(1.0, repeated_events / 3.0)

    raw_score = (0.40 * ratio_term + 0.35 * duration_term + 0.25 * repeated_term) * 100.0
    return round(min(100.0, max(0.0, raw_score)), 1)


def compute_shelf_metrics(
    events: List[AttentionEventRecord],
    configured_shelves: List[dict],
    zone_dwell_map: Optional[Dict[str, float]] = None,
    zone_visitor_map: Optional[Dict[str, int]] = None,
    store_id: Optional[str] = None,
    camera_id: Optional[str] = None,
) -> List[ShelfEngagement]:
    """
    Aggregate attention metrics per shelf.
    """
    dwell_map = zone_dwell_map or {}
    visitor_map = zone_visitor_map or {}

    shelf_records: Dict[str, ShelfEngagement] = {}

    # Initialize all configured shelves
    for s in configured_shelves:
        s_id = str(s.get("id") or s.get("shelf_id") or "")
        s_name = str(s.get("name") or s.get("shelf_name") or "Unknown Shelf")
        s_zone = str(s.get("zone_id") or "")
        if s_id:
            # Resolve dwell time and visitors: try direct match, s_zone, or shelf_X -> zone_X
            resolved_dwell = dwell_map.get(s_id)
            resolved_visitors = visitor_map.get(s_id)
            if resolved_dwell is None and s_zone:
                resolved_dwell = dwell_map.get(s_zone)
                resolved_visitors = visitor_map.get(s_zone)
            if resolved_dwell is None and s_id.startswith("shelf_"):
                alt_zone = s_id.replace("shelf_", "zone_")
                resolved_dwell = dwell_map.get(alt_zone)
                resolved_visitors = visitor_map.get(alt_zone)

            shelf_records[s_id] = ShelfEngagement(
                shelf_id=s_id,
                shelf_name=s_name,
                store_id=store_id,
                camera_id=camera_id,
                visitors=resolved_visitors or 0,
                dwell_time_sec=resolved_dwell or 0.0,
            )

    # Accumulate from attention events
    track_shelf_visits: Dict[str, set] = {}
    shelf_event_tracks: Dict[str, set] = {}

    for ev in events:
        if ev.target_type == "shelf" or ev.target_id in shelf_records:
            s_id = ev.target_id
            if s_id not in shelf_records:
                shelf_records[s_id] = ShelfEngagement(
                    shelf_id=s_id,
                    shelf_name=ev.target_name,
                    store_id=store_id,
                    camera_id=camera_id,
                    visitors=visitor_map.get(ev.zone_id, 0),
                    dwell_time_sec=dwell_map.get(ev.zone_id, 0.0),
                )

            rec = shelf_records[s_id]
            # If dwell_time_sec is still 0 and event has a valid zone_id, correlate with zone dwell
            if rec.dwell_time_sec == 0.0 and ev.zone_id in dwell_map:
                rec.dwell_time_sec = dwell_map[ev.zone_id]
                if rec.visitors == 0:
                    rec.visitors = visitor_map.get(ev.zone_id, 0)

            dur = ev.duration_seconds or 0.0
            rec.shelf_attention_time_sec += dur
            rec.attention_event_count += 1

            if s_id not in shelf_event_tracks:
                shelf_event_tracks[s_id] = set()
            shelf_event_tracks[s_id].add(ev.track_id)

            if ev.visit_number > 1:
                rec.repeated_attention_events += 1

    # Finalize calculations
    result_list = []
    for s_id, rec in shelf_records.items():
        rec.viewers = len(shelf_event_tracks.get(s_id, set()))
        if rec.visitors < rec.viewers:
            rec.visitors = rec.viewers

        if rec.attention_event_count > 0:
            rec.average_shelf_attention_sec = round(
                rec.shelf_attention_time_sec / rec.attention_event_count, 2
            )

        rec.score = calculate_shelf_engagement_score(
            shelf_attention_time_sec=rec.shelf_attention_time_sec,
            dwell_time_sec=rec.dwell_time_sec,
            repeated_events=rec.repeated_attention_events,
        )
        result_list.append(rec)

    result_list.sort(key=lambda s: s.shelf_attention_time_sec, reverse=True)
    return result_list


def compute_product_metrics(
    events: List[AttentionEventRecord],
    configured_products: Optional[List[dict]] = None,
    is_spatial_mapping_active: bool = False,
) -> List[ProductAttention]:
    """
    Aggregate product focus metrics if spatial product polygons are active.
    Otherwise returns placeholders marked as 'Unavailable / Not Configured'.
    """
    if not is_spatial_mapping_active or not configured_products:
        results = []
        if configured_products:
            for p in configured_products:
                results.append(
                    ProductAttention(
                        product_id=str(p.get("id", "")),
                        product_name=str(p.get("name", "Unknown Product")),
                        sku=p.get("sku"),
                        shelf_id=str(p.get("shelf_id", "")),
                        shelf_name=p.get("shelf_name"),
                        is_configured=False,
                        status_note="Unavailable / Not Configured",
                    )
                )
        return results

    prod_map: Dict[str, ProductAttention] = {}
    for p in configured_products:
        p_id = str(p.get("id", ""))
        if p_id:
            prod_map[p_id] = ProductAttention(
                product_id=p_id,
                product_name=str(p.get("name", "Unknown Product")),
                sku=p.get("sku"),
                shelf_id=str(p.get("shelf_id", "")),
                shelf_name=p.get("shelf_name"),
                is_configured=True,
                status_note="Configured",
            )

    prod_tracks: Dict[str, set] = {}
    for ev in events:
        if ev.target_type == "product" and ev.target_id in prod_map:
            p_id = ev.target_id
            rec = prod_map[p_id]
            dur = ev.duration_seconds or 0.0
            rec.total_focus_duration_sec += dur
            rec.attention_events += 1

            if p_id not in prod_tracks:
                prod_tracks[p_id] = set()
            prod_tracks[p_id].add(ev.track_id)

            if ev.visit_number > 1:
                rec.repeated_attention_events += 1

    result_list = []
    for p_id, rec in prod_map.items():
        rec.viewers = len(prod_tracks.get(p_id, set()))
        if rec.attention_events > 0:
            rec.average_focus_duration_sec = round(
                rec.total_focus_duration_sec / rec.attention_events, 2
            )
        result_list.append(rec)

    result_list.sort(key=lambda p: p.total_focus_duration_sec, reverse=True)
    return result_list
