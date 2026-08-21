"""
Module 5 — Product Interaction Detector
=========================================
Detects and deduplicates PRODUCT_VIEWED events from Module 4 attention outputs
and spatial product/shelf mappings while maintaining strict multi-person
ByteTrack separation.
"""

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.module5.models import (
    InteractionEventType,
    InteractionSource,
    ProductInteractionEvent,
)


class Module5InteractionDetector:
    """
    Detects product view and engagement events from Module 4 attention events.
    """

    def __init__(
        self,
        dedup_gap_threshold_sec: float = 1.0,
        min_view_duration_sec: float = 0.20,
    ):
        self.dedup_gap_threshold_sec = dedup_gap_threshold_sec
        self.min_view_duration_sec = min_view_duration_sec

    def extract_product_view_events(
        self,
        attention_events: List[Dict[str, Any]],
        products_by_shelf: Dict[str, List[Dict[str, Any]]],
        products_by_id: Dict[str, Dict[str, Any]],
        camera_id: Optional[str] = None,
        store_id: Optional[str] = None,
    ) -> List[ProductInteractionEvent]:
        """
        Derive PRODUCT_VIEWED events from Module 4 attention events.
        
        Parameters
        ----------
        attention_events : List[Dict[str, Any]]
            Raw attention events from Module 4 / Phase 5.
        products_by_shelf : Dict[str, List[Dict[str, Any]]]
            Mapping from shelf_id/shelf_code to associated products.
        products_by_id : Dict[str, Dict[str, Any]]
            Lookup of products by product_id.
        camera_id : Optional[str]
            Active camera ID.
        store_id : Optional[str]
            Active store ID.
        
        Returns
        -------
        List[ProductInteractionEvent]
            Deduplicated, structured product view interaction events.
        """
        raw_view_events: List[ProductInteractionEvent] = []

        for ev in attention_events:
            track_id = int(ev.get("track_id") or ev.get("tracking_id", 0))
            if track_id <= 0:
                continue

            session_id = ev.get("session_id")
            target_type = str(ev.get("target_type", "shelf")).lower()
            target_id = str(ev.get("target_id", "unknown"))
            target_name = str(ev.get("target_name", "Unknown"))
            start_time = float(ev.get("start_time", 0.0) or ev.get("timestamp", 0.0))
            end_time = float(ev.get("end_time", start_time + float(ev.get("duration_seconds", 0.0) or 0.0)))
            duration = max(0.0, end_time - start_time)
            confidence = float(ev.get("confidence", 0.8))

            if duration < self.min_view_duration_sec:
                continue

            # Case A: Direct Product Target from Module 4
            if target_type == "product" and target_id in products_by_id:
                p = products_by_id[target_id]
                event = ProductInteractionEvent(
                    event_id=f"EVT_VIEW_{track_id}_{start_time:.2f}_{p['id']}",
                    event_type=InteractionEventType.PRODUCT_VIEWED,
                    track_id=track_id,
                    session_id=session_id,
                    store_id=store_id,
                    camera_id=camera_id,
                    product_id=p["id"],
                    product_name=p["name"],
                    sku=p.get("sku"),
                    shelf_id=p.get("shelf_id") or target_id,
                    shelf_name=p.get("shelf_name") or target_name,
                    timestamp=start_time,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    confidence=confidence,
                    source=InteractionSource.MODULE_4_ATTENTION,
                    metadata={
                        "target_type": "product",
                        "attention_direction": ev.get("attention_direction", "UNKNOWN"),
                        "spatial_mapped": True,
                    },
                )
                raw_view_events.append(event)

            # Case B: Shelf Target with associated products
            elif target_type in ("shelf", "unknown", "zone"):
                shelf_id = target_id
                shelf_name = target_name
                matched_products = products_by_shelf.get(shelf_id, [])

                if matched_products:
                    # When a shelf is viewed, create view records for products on that shelf
                    for p in matched_products:
                        event = ProductInteractionEvent(
                            event_id=f"EVT_VIEW_{track_id}_{start_time:.2f}_{p['id']}",
                            event_type=InteractionEventType.PRODUCT_VIEWED,
                            track_id=track_id,
                            session_id=session_id,
                            store_id=store_id,
                            camera_id=camera_id,
                            product_id=p["id"],
                            product_name=p["name"],
                            sku=p.get("sku"),
                            shelf_id=shelf_id,
                            shelf_name=shelf_name,
                            timestamp=start_time,
                            start_time=start_time,
                            end_time=end_time,
                            duration_seconds=duration,
                            confidence=confidence,
                            source=InteractionSource.MODULE_4_ATTENTION,
                            metadata={
                                "target_type": "shelf_associated_product",
                                "shelf_id": shelf_id,
                                "shelf_name": shelf_name,
                                "attention_direction": ev.get("attention_direction", "UNKNOWN"),
                                "spatial_mapped": False,
                            },
                        )
                        raw_view_events.append(event)
                elif shelf_id != "unknown":
                    # Shelf viewed with no DB products assigned
                    event = ProductInteractionEvent(
                        event_id=f"EVT_VIEW_{track_id}_{start_time:.2f}_{shelf_id}",
                        event_type=InteractionEventType.PRODUCT_VIEWED,
                        track_id=track_id,
                        session_id=session_id,
                        store_id=store_id,
                        camera_id=camera_id,
                        product_id=None,
                        product_name=None,
                        sku=None,
                        shelf_id=shelf_id,
                        shelf_name=shelf_name,
                        timestamp=start_time,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration,
                        confidence=confidence,
                        source=InteractionSource.MODULE_4_ATTENTION,
                        metadata={
                            "target_type": "shelf",
                            "shelf_id": shelf_id,
                            "attention_direction": ev.get("attention_direction", "UNKNOWN"),
                        },
                    )
                    raw_view_events.append(event)

        # Deduplicate consecutive/overlapping events per (track_id, product_id, shelf_id)
        return self.deduplicate_events(raw_view_events)

    def deduplicate_events(
        self,
        events: List[ProductInteractionEvent],
    ) -> List[ProductInteractionEvent]:
        """
        Merge consecutive or overlapping events for the same shopper and product/shelf
        if the gap between them is within dedup_gap_threshold_sec.
        Never merges different shoppers (track_ids).
        """
        if not events:
            return []

        # Sort by track_id, product_id, shelf_id, start_time
        events_sorted = sorted(
            events,
            key=lambda e: (
                e.track_id,
                e.product_id or "",
                e.shelf_id or "",
                e.start_time,
            ),
        )

        deduped: List[ProductInteractionEvent] = []
        current = events_sorted[0]

        for nxt in events_sorted[1:]:
            same_shopper = (current.track_id == nxt.track_id)
            same_product = (current.product_id == nxt.product_id)
            same_shelf = (current.shelf_id == nxt.shelf_id)
            same_type = (current.event_type == nxt.event_type)

            curr_end = current.end_time if current.end_time is not None else current.start_time + current.duration_seconds
            gap = nxt.start_time - curr_end

            if same_shopper and same_product and same_shelf and same_type and gap <= self.dedup_gap_threshold_sec:
                # Merge into current
                new_end = max(curr_end, nxt.end_time if nxt.end_time is not None else nxt.start_time + nxt.duration_seconds)
                current.end_time = new_end
                current.duration_seconds = max(0.0, new_end - current.start_time)
                current.confidence = max(current.confidence, nxt.confidence)
            else:
                deduped.append(current)
                current = nxt

        deduped.append(current)

        # Final sort by start_time
        deduped.sort(key=lambda e: (e.start_time, e.track_id))
        return deduped
