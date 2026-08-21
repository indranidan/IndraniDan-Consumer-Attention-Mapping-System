"""
Module 5 — Product Comparison Analyzer
========================================
Identifies multi-product consideration journeys and comparison patterns
when a single shopper interacts with or attends to multiple products or shelves
within the same session.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from app.module5.models import (
    InteractionEventType,
    InteractionSource,
    ProductComparisonPattern,
    ProductInteractionEvent,
)


class Module5ComparisonAnalyzer:
    """
    Analyzes temporal sequences of product interactions per shopper session
    to identify consideration and comparison behavior.
    """

    def __init__(
        self,
        max_comparison_gap_sec: float = 60.0,
    ):
        self.max_comparison_gap_sec = max_comparison_gap_sec

    def analyze_comparisons(
        self,
        events: List[ProductInteractionEvent],
        camera_id: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> Tuple[List[ProductComparisonPattern], List[ProductInteractionEvent]]:
        """
        Extract observed multi-product interaction patterns and comparison events.
        
        Parameters
        ----------
        events : List[ProductInteractionEvent]
            Chronological interaction events (views, pickups, returns).
        
        Returns
        -------
        Tuple[List[ProductComparisonPattern], List[ProductInteractionEvent]]
            (comparison_patterns, product_compared_events)
        """
        # Group events by (track_id, session_id)
        shopper_events: Dict[Tuple[int, Optional[str]], List[ProductInteractionEvent]] = {}
        for ev in events:
            # Consider VIEWED, PICKED_UP, or RETURNED events with a target product or shelf
            target_key = ev.product_name or ev.shelf_name
            if target_key:
                shopper_events.setdefault((ev.track_id, ev.session_id), []).append(ev)

        patterns: List[ProductComparisonPattern] = []
        compared_events: List[ProductInteractionEvent] = []

        pattern_idx = 1
        for (track_id, session_id), s_events in shopper_events.items():
            if len(s_events) < 2:
                continue

            # Sort chronologically
            s_events.sort(key=lambda e: e.start_time)

            # Check distinct products or distinct shelves in session
            distinct_targets: Set[str] = set()
            for e in s_events:
                name = e.product_name or e.shelf_name or "Unknown"
                distinct_targets.add(name)

            # If shopper viewed/interacted with >= 2 distinct items
            if len(distinct_targets) >= 2:
                # Build interaction sequence
                seq: List[Dict[str, Any]] = []
                for e in s_events:
                    seq.append({
                        "product_id": e.product_id,
                        "product_name": e.product_name or e.shelf_name or "Unknown",
                        "shelf_id": e.shelf_id,
                        "event_type": e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                        "start_time": round(e.start_time, 2),
                        "end_time": round(e.end_time, 2) if e.end_time is not None else None,
                        "duration_seconds": round(e.duration_seconds, 2),
                    })

                start_t = s_events[0].start_time
                end_t = s_events[-1].end_time if s_events[-1].end_time is not None else s_events[-1].start_time + s_events[-1].duration_seconds
                total_dur = max(0.0, end_t - start_t)

                prod_ids = [e.product_id for e in s_events if e.product_id] or [e.shelf_id for e in s_events if e.shelf_id]
                prod_names = list(distinct_targets)

                seq_str = " -> ".join([s["product_name"] for s in seq])
                description = f"Observed multi-product interaction: {seq_str} ({len(distinct_targets)} unique items)"

                pattern = ProductComparisonPattern(
                    pattern_id=f"CMP_PAT_{track_id}_{pattern_idx:03d}",
                    session_id=session_id,
                    track_id=track_id,
                    product_ids=list(set(prod_ids)),
                    product_names=prod_names,
                    interaction_sequence=seq,
                    total_duration_sec=total_dur,
                    start_time=start_t,
                    end_time=end_t,
                    pattern_description=description,
                )
                patterns.append(pattern)

                # Also create a PRODUCT_COMPARED interaction event
                comp_evt = ProductInteractionEvent(
                    event_id=f"EVT_COMPARE_{track_id}_{start_t:.2f}_{pattern.pattern_id}",
                    event_type=InteractionEventType.PRODUCT_COMPARED,
                    track_id=track_id,
                    session_id=session_id,
                    store_id=store_id,
                    camera_id=camera_id,
                    product_id=prod_ids[0] if prod_ids else None,
                    product_name=", ".join(prod_names[:3]),
                    sku=None,
                    shelf_id=s_events[0].shelf_id,
                    shelf_name=s_events[0].shelf_name,
                    timestamp=start_t,
                    start_time=start_t,
                    end_time=end_t,
                    duration_seconds=total_dur,
                    confidence=0.90,
                    source=InteractionSource.BEHAVIORAL_HEURISTIC,
                    metadata={
                        "pattern_id": pattern.pattern_id,
                        "unique_items_count": len(distinct_targets),
                        "items_compared": prod_names,
                        "sequence_steps": len(seq),
                    },
                )
                compared_events.append(comp_evt)
                pattern_idx += 1

        return patterns, compared_events
