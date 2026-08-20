"""
Module 4 — Attention Aggregator
=================================
Aggregates attention metrics across dimensions:
Store, Camera, Zone, Shelf, Product, Session, and Job.
"""

from typing import Any, Dict, List, Optional
from app.module4.models import (
    AttentionEventRecord,
    AttentionQualityMetrics,
    Module4Summary,
    ProductAttention,
    ShelfEngagement,
)


class Module4Aggregator:
    """Aggregates attention events into cohesive summaries."""

    def __init__(self):
        pass

    def aggregate_all(
        self,
        events: List[AttentionEventRecord],
        shelves: List[ShelfEngagement],
        products: List[ProductAttention],
        quality: Optional[AttentionQualityMetrics] = None,
        total_dwell_sec: float = 0.0,
    ) -> Module4Summary:
        """
        Aggregate complete Module 4 summary metrics.
        """
        total_events = len(events)
        total_attn_dur = sum(e.duration_seconds or 0.0 for e in events)
        avg_attn_dur = (total_attn_dur / total_events) if total_events > 0 else 0.0

        total_shelf_attn = sum(s.shelf_attention_time_sec for s in shelves)
        total_prod_focus = sum(p.total_focus_duration_sec for p in products if p.is_configured)
        repeated_events = sum(1 for e in events if e.visit_number > 1)

        unique_viewers = len(set(e.track_id for e in events))

        most_attended_shelf = None
        if shelves and shelves[0].shelf_attention_time_sec > 0:
            most_attended_shelf = {
                "shelf_id": shelves[0].shelf_id,
                "shelf_name": shelves[0].shelf_name,
                "attention_time_sec": shelves[0].shelf_attention_time_sec,
                "event_count": shelves[0].attention_event_count,
                "score": shelves[0].score,
            }

        avg_score = (sum(s.score for s in shelves) / len(shelves)) if shelves else 0.0
        prod_configured = any(p.is_configured for p in products)

        return Module4Summary(
            total_attention_events=total_events,
            total_attention_duration_sec=total_attn_dur,
            average_attention_duration_sec=avg_attn_dur,
            total_dwell_time_sec=total_dwell_sec,
            total_shelf_attention_time_sec=total_shelf_attn,
            total_product_focus_duration_sec=total_prod_focus,
            total_repeated_attention_events=repeated_events,
            total_unique_viewers=unique_viewers,
            most_attended_shelf=most_attended_shelf,
            shelf_engagement_score_avg=avg_score,
            product_mapping_configured=prod_configured,
        )
