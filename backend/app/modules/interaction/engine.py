"""
Module 5 — Product Interaction Analysis Master Engine
======================================================
Orchestrates:
1. Product Viewed Detection & Deduplication (from Module 4 attention data)
2. Product Pickup & Return Detection (with visual evidence gating)
3. Shelf Interaction Monitoring (Visits vs Attention vs Interactions vs Touch)
4. Product Engagement Matrix Computation
5. Multi-Product Comparison & Consideration Pattern Analysis
6. Structured Report Generation (JSON & Markdown)

Reuses existing Module 3 and Module 4 outputs without re-running YOLO or ByteTrack.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.modules.interaction.comparison_analyzer import Module5ComparisonAnalyzer
from app.modules.interaction.interaction_detector import Module5InteractionDetector
from app.modules.interaction.models import (
    InteractionEventType,
    Module5Summary,
    ProductComparisonPattern,
    ProductEngagementMetric,
    ProductInteractionEvent,
    ShelfInteractionMetric,
)
from app.modules.interaction.pickup_return_detector import Module5PickupReturnDetector
from app.modules.interaction.report_generator import Module5ReportGenerator
from app.modules.interaction.shelf_interaction_monitor import Module5ShelfInteractionMonitor


class Module5InteractionEngine:
    """
    Dedicated Product Interaction Analysis Engine for Module 5.
    """

    def __init__(
        self,
        dedup_gap_threshold_sec: float = 1.0,
        min_view_duration_sec: float = 0.20,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger("module5_engine")
        self.interaction_detector = Module5InteractionDetector(
            dedup_gap_threshold_sec=dedup_gap_threshold_sec,
            min_view_duration_sec=min_view_duration_sec,
        )
        self.pickup_return_detector = Module5PickupReturnDetector()
        self.comparison_analyzer = Module5ComparisonAnalyzer()
        self.shelf_monitor = Module5ShelfInteractionMonitor()
        self.report_generator = Module5ReportGenerator()

    def process_completed_job(
        self,
        job_output_dir: Path,
        configured_shelves: Optional[List[Dict[str, Any]]] = None,
        configured_products: Optional[List[Dict[str, Any]]] = None,
        product_mappings: Optional[List[Dict[str, Any]]] = None,
        store_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        pos_transactions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze product interactions for a completed AI job using Module 3 & Module 4 outputs.
        NO YOLOv8 or ByteTrack execution is performed.

        Parameters
        ----------
        job_output_dir : Path
            Path to the job output directory (e.g. outputs/ai_jobs/{job_id}).
        configured_shelves : Optional[List[Dict[str, Any]]]
            List of shelf configurations from DB / config file.
        configured_products : Optional[List[Dict[str, Any]]]
            List of products for the store from DB.
        product_mappings : Optional[List[Dict[str, Any]]]
            List of spatial product polygon mappings if configured.
        store_id : Optional[str]
            Parent store ID.
        camera_id : Optional[str]
            Camera ID.
        pos_transactions : Optional[List[Dict[str, Any]]]
            External POS transaction records if available.

        Returns
        -------
        Dict[str, Any]
            Complete Module 5 report dictionary.
        """
        self.logger.info(f"Module 5 analyzing product interactions from {job_output_dir}")

        # ── 1. Load Module 4 Attention Events ──────────────────────────
        attention_events: List[Dict[str, Any]] = []

        # Candidate paths for attention events
        m4_candidates = [
            job_output_dir / "module4" / "module4_attention_report.json",
            job_output_dir / "module4_attention_report.json",
        ]
        p5_candidates = [
            job_output_dir / "phase5" / "reports" / "attention_events.json",
            job_output_dir / "phase5" / "attention_events.json",
            job_output_dir / "reports" / "attention_events.json",
        ]

        for m4_file in m4_candidates:
            if m4_file.exists():
                try:
                    with open(m4_file, "r", encoding="utf-8") as f:
                        m4_data = json.load(f)
                        attention_events = m4_data.get("events_sample", [])
                        if attention_events:
                            break
                except Exception as exc:
                    self.logger.warning(f"Could not load {m4_file}: {exc}")

        if not attention_events:
            for p5_file in p5_candidates:
                if p5_file.exists():
                    try:
                        with open(p5_file, "r", encoding="utf-8") as f:
                            p5_data = json.load(f)
                            attention_events = p5_data.get("events", [])
                            if attention_events:
                                break
                    except Exception as exc:
                        self.logger.warning(f"Could not load {p5_file}: {exc}")

        # ── 2. Load Module 3 Spatial, Path & Dwell Data ────────────────
        zone_visits: List[Dict[str, Any]] = []
        p3_zv_candidates = [
            job_output_dir / "phase3" / "reports" / "zone_visits.json",
            job_output_dir / "phase3" / "zone_visits.json",
            job_output_dir / "reports" / "zone_visits.json",
        ]
        for p3_zv_file in p3_zv_candidates:
            if p3_zv_file.exists():
                try:
                    with open(p3_zv_file, "r", encoding="utf-8") as f:
                        p3_zv_data = json.load(f)
                        zone_visits = p3_zv_data.get("zone_visits", [])
                        if zone_visits:
                            break
                except Exception as exc:
                    self.logger.warning(f"Could not load zone_visits from {p3_zv_file}: {exc}")

        paths_data: Dict[str, List[Dict[str, Any]]] = {}
        p3_paths_candidates = [
            job_output_dir / "phase3" / "reports" / "paths.json",
            job_output_dir / "phase3" / "paths.json",
            job_output_dir / "reports" / "paths.json",
        ]
        for p3_paths_file in p3_paths_candidates:
            if p3_paths_file.exists():
                try:
                    with open(p3_paths_file, "r", encoding="utf-8") as f:
                        p3_paths_raw = json.load(f)
                        paths_data = p3_paths_raw.get("paths", {})
                        if paths_data:
                            break
                except Exception as exc:
                    self.logger.warning(f"Could not load paths from {p3_paths_file}: {exc}")

        zone_dwell_map: Dict[str, float] = {}
        zone_visitor_map: Dict[str, int] = {}
        p4_zd_candidates = [
            job_output_dir / "phase4" / "reports" / "zone_dwell_summary.json",
            job_output_dir / "phase4" / "zone_dwell_summary.json",
            job_output_dir / "reports" / "zone_dwell_summary.json",
        ]
        for p4_zd_file in p4_zd_candidates:
            if p4_zd_file.exists():
                try:
                    with open(p4_zd_file, "r", encoding="utf-8") as f:
                        p4_data = json.load(f)
                        for z in (p4_data.get("zone_summaries") or p4_data.get("zones", [])):
                            z_id = z.get("zone_id")
                            if z_id:
                                zone_dwell_map[z_id] = float(z.get("total_dwell_seconds", 0.0))
                                zone_visitor_map[z_id] = int(z.get("unique_shoppers", 0))
                        break
                except Exception as exc:
                    self.logger.warning(f"Could not load zone_dwell_summary from {p4_zd_file}: {exc}")

        # ── 3. Resolve Product & Shelf Mappings ────────────────────────
        shelves_list = configured_shelves or []
        products_list = configured_products or []

        products_by_shelf: Dict[str, List[Dict[str, Any]]] = {}
        products_by_id: Dict[str, Dict[str, Any]] = {}

        for p in products_list:
            p_id = str(p.get("id") or p.get("product_id") or "")
            if p_id:
                products_by_id[p_id] = p
            sh_id = str(p.get("shelf_id") or "")
            if sh_id:
                products_by_shelf.setdefault(sh_id, []).append(p)
            sh_code = str(p.get("shelf_code") or "")
            if sh_code and sh_code != sh_id:
                products_by_shelf.setdefault(sh_code, []).append(p)

        # ── 4. Detect PRODUCT_VIEWED Events ───────────────────────────
        view_events = self.interaction_detector.extract_product_view_events(
            attention_events=attention_events,
            products_by_shelf=products_by_shelf,
            products_by_id=products_by_id,
            camera_id=camera_id,
            store_id=store_id,
        )

        # ── 5. Detect PICKUPS, RETURNS & PURCHASES ─────────────────────
        other_events, pickup_status, purchase_status = self.pickup_return_detector.detect_pickups_and_returns(
            view_events=view_events,
            tracking_paths=paths_data,
            zone_visits=zone_visits,
            shelf_regions=shelves_list,
            pos_transactions=pos_transactions,
            has_high_res_hand_tracking=False,  # Video CCTV evidence gating
            camera_id=camera_id,
            store_id=store_id,
        )

        all_base_events = view_events + other_events

        # ── 6. Analyze MULTI-PRODUCT COMPARISONS ───────────────────────
        comparison_patterns, comparison_events = self.comparison_analyzer.analyze_comparisons(
            events=all_base_events,
            camera_id=camera_id,
            store_id=store_id,
        )

        all_events = all_base_events + comparison_events
        all_events.sort(key=lambda e: (e.start_time, e.track_id))

        # ── 7. Compute Shelf & Product Metrics ────────────────────────
        shelf_metrics = self.shelf_monitor.compute_shelf_interactions(
            events=all_events,
            configured_shelves=shelves_list,
            zone_visits=zone_visits,
            zone_dwell_map=zone_dwell_map,
            zone_visitor_map=zone_visitor_map,
            products_by_shelf=products_by_shelf,
        )

        is_spatial_mapped = bool(product_mappings and len(product_mappings) > 0)
        product_metrics = self.shelf_monitor.compute_product_engagement(
            events=all_events,
            all_products=products_list,
            comparison_events=comparison_events,
            is_spatial_mapped=is_spatial_mapped,
        )

        # ── 8. Aggregate Summary ──────────────────────────────────────
        total_views = sum(1 for e in all_events if e.event_type == InteractionEventType.PRODUCT_VIEWED)
        total_pickups = sum(1 for e in all_events if e.event_type == InteractionEventType.PRODUCT_PICKED_UP)
        total_returns = sum(1 for e in all_events if e.event_type == InteractionEventType.PRODUCT_RETURNED)
        total_purchases = sum(1 for e in all_events if e.event_type == InteractionEventType.PRODUCT_PURCHASED)
        total_comparisons = len(comparison_patterns)

        unique_viewers = len({e.track_id for e in all_events if e.event_type == InteractionEventType.PRODUCT_VIEWED})
        total_view_duration = sum(e.duration_seconds for e in all_events if e.event_type == InteractionEventType.PRODUCT_VIEWED)
        avg_view_duration = (total_view_duration / total_views) if total_views > 0 else 0.0

        total_engagement_dur = sum(s.total_engagement_duration_sec for s in shelf_metrics)
        total_shelf_interactions = sum(s.shelf_interactions for s in shelf_metrics)

        summary = Module5Summary(
            total_views=total_views,
            total_unique_viewers=unique_viewers,
            total_view_duration_sec=total_view_duration,
            average_view_duration_sec=avg_view_duration,
            total_pickups=total_pickups,
            total_returns=total_returns,
            total_comparisons=total_comparisons,
            total_purchases=total_purchases,
            total_shelf_interactions=total_shelf_interactions,
            total_engagement_duration_sec=total_engagement_dur,
            pickup_detection_status=pickup_status,
            purchase_data_status=purchase_status,
            product_mapping_configured=is_spatial_mapped,
        )

        # ── 9. Generate and Save Reports ──────────────────────────────
        job_meta = {
            "job_directory": str(job_output_dir),
            "store_id": store_id,
            "camera_id": camera_id,
        }

        report_data = self.report_generator.generate_json_report(
            summary=summary,
            products=product_metrics,
            shelves=shelf_metrics,
            events=all_events,
            comparisons=comparison_patterns,
            job_metadata=job_meta,
        )

        m5_dir = job_output_dir / "module5"
        self.report_generator.write_reports(report_data, m5_dir)
        self.logger.info(f"Module 5 reports successfully saved to {m5_dir}")

        return report_data
