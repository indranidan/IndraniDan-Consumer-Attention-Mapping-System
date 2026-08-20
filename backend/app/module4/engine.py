"""
Module 4 — Attention Analysis Master Engine
============================================
Orchestrates:
1. Gaze Estimation
2. Head Pose Analysis
3. Shelf Engagement Analysis
4. Product Attention Detection
5. Attention Duration & Metrics
6. Attention Reports & Heatmaps

Reuses existing Module 3 outputs without re-running YOLOv8 or ByteTrack.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from app.module4.aggregator import Module4Aggregator
from app.module4.event_detector import Module4AttentionEventDetector
from app.module4.gaze_estimator import Module4GazeEstimator
from app.module4.head_pose import Module4HeadPoseEstimator
from app.module4.heatmap_generator import Module4HeatmapGenerator
from app.module4.metrics import compute_product_metrics, compute_shelf_metrics
from app.module4.models import (
    AttentionEventRecord,
    AttentionQualityMetrics,
    GazeEstimate,
    HeadPoseData,
    Module4Summary,
    ProductAttention,
    ShelfEngagement,
)
from app.module4.product_attention import Module4ProductAttentionDetector
from app.module4.report_generator import Module4ReportGenerator
from app.module4.shelf_engagement import Module4ShelfEngagementAnalyzer


class Module4AttentionEngine:
    """
    Dedicated Attention Analysis Engine for Module 4.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.50,
        yaw_threshold: float = 15.0,
        pitch_threshold: float = 15.0,
        min_event_duration: float = 0.30,
        max_ray_distance: int = 500,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger("module4_engine")
        self.confidence_threshold = confidence_threshold

        self.head_pose_estimator = Module4HeadPoseEstimator(
            min_detection_confidence=confidence_threshold,
            logger=self.logger,
        )
        self.gaze_estimator = Module4GazeEstimator(
            yaw_threshold=yaw_threshold,
            pitch_threshold=pitch_threshold,
            confidence_threshold=confidence_threshold,
        )
        self.shelf_analyzer = Module4ShelfEngagementAnalyzer(
            max_ray_distance=max_ray_distance,
        )
        self.product_detector = Module4ProductAttentionDetector(
            max_ray_distance=max_ray_distance,
        )
        self.event_detector = Module4AttentionEventDetector(
            min_duration_sec=min_event_duration,
        )
        self.aggregator = Module4Aggregator()
        self.report_generator = Module4ReportGenerator()
        self.heatmap_generator = Module4HeatmapGenerator()

    def configure_spatial_regions(
        self,
        shelf_regions: List[dict],
        product_mappings: Optional[List[dict]] = None,
    ) -> None:
        """Configure camera-specific shelf regions and product spatial polygons."""
        self.shelf_analyzer.load_from_dict_list(shelf_regions)
        self.product_detector.load_product_mappings(product_mappings or [])

    def process_completed_module3_job(
        self,
        job_output_dir: Path,
        shelf_regions: Optional[List[dict]] = None,
        product_mappings: Optional[List[dict]] = None,
        store_id: Optional[str] = None,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a completed Module 3 job using its stored artifacts.
        NO YOLOv8 or ByteTrack execution is performed.

        Parameters
        ----------
        job_output_dir : Path
            Path to the job output directory (e.g. outputs/ai_jobs/{job_id}).
        shelf_regions : Optional[List[dict]]
            Configured shelf polygon definitions.
        product_mappings : Optional[List[dict]]
            Configured product polygon definitions.
        store_id : Optional[str]
            Parent store ID.
        camera_id : Optional[str]
            Analyzed camera ID.

        Returns
        -------
        Dict[str, Any]
            Complete Module 4 report object and analytics.
        """
        self.logger.info(f"Module 4 analyzing completed Module 3 job from {job_output_dir}")

        if shelf_regions is not None:
            self.configure_spatial_regions(shelf_regions, product_mappings)

        # 1. Read Phase 4 dwell data for zone dwell times
        zone_dwell_map: Dict[str, float] = {}
        zone_visitor_map: Dict[str, int] = {}
        total_dwell_sec = 0.0

        p4_dir = job_output_dir / "phase4" / "reports"
        p4_file = p4_dir / "zone_dwell_summary.json"
        if p4_file.exists():
            try:
                with open(p4_file, "r", encoding="utf-8") as f:
                    p4_data = json.load(f)
                    for z in p4_data.get("zones", []):
                        z_id = z.get("zone_id")
                        if z_id:
                            dwell = float(z.get("total_dwell_seconds", 0.0))
                            zone_dwell_map[z_id] = dwell
                            zone_visitor_map[z_id] = int(z.get("unique_shoppers", 0))
                            total_dwell_sec += dwell
            except Exception as exc:
                self.logger.warning(f"Could not load Phase 4 zone dwell summary: {exc}")

        # 2. Read Phase 5 attention events
        p5_events_file = job_output_dir / "phase5" / "reports" / "attention_events.json"
        events: List[AttentionEventRecord] = []

        if p5_events_file.exists():
            try:
                with open(p5_events_file, "r", encoding="utf-8") as f:
                    p5_data = json.load(f)
                    raw_events = p5_data.get("events", [])
                    for re in raw_events:
                        ev = AttentionEventRecord(
                            event_id=re.get("event_id") or str(re.get("tracking_id", "")) + "_" + str(re.get("start_time", "")),
                            track_id=re.get("tracking_id", 0),
                            session_id=re.get("session_id"),
                            camera_id=camera_id,
                            store_id=store_id,
                            timestamp=re.get("start_time", 0.0),
                            start_time=re.get("start_time", 0.0),
                            end_time=re.get("end_time"),
                            duration_seconds=re.get("duration_seconds"),
                            attention_type=re.get("attention_type", "SHELF_ATTENTION"),
                            target_type=re.get("target_type", "shelf"),
                            target_id=re.get("target_id", "unknown"),
                            target_name=re.get("target_name", "Unknown"),
                            zone_id=re.get("zone_id", "unknown"),
                            attention_direction=re.get("attention_direction", "UNKNOWN"),
                            confidence=float(re.get("confidence", 0.0)),
                            status=re.get("status", "completed"),
                            visit_number=int(re.get("visit_number", 1)),
                            start_frame=int(re.get("start_frame", 0)),
                            end_frame=re.get("end_frame"),
                            gaze_origin=tuple(re["gaze_origin"]) if "gaze_origin" in re and re["gaze_origin"] else None,
                            gaze_direction=tuple(re["gaze_direction"]) if "gaze_direction" in re and re["gaze_direction"] else None,
                        )
                        events.append(ev)
            except Exception as exc:
                self.logger.warning(f"Could not load Phase 5 attention events: {exc}")

        # 2b. Backfill gaze_origin from Phase 2 tracks when Phase 5 events lack spatial coordinates
        events_missing_origin = [e for e in events if not e.gaze_origin]
        if events_missing_origin:
            p2_tracks_file = job_output_dir / "phase2" / "reports" / "tracks.json"
            if p2_tracks_file.exists():
                try:
                    with open(p2_tracks_file, "r", encoding="utf-8") as f:
                        p2_data = json.load(f)
                    # Build frame -> {track_id: track_info} lookup
                    frame_track_map: Dict[int, Dict[int, dict]] = {}
                    for frame_entry in p2_data.get("frames", []):
                        frame_num = frame_entry.get("frame", 0)
                        tracks_in_frame: Dict[int, dict] = {}
                        for t in frame_entry.get("tracks", []):
                            tracks_in_frame[t.get("track_id", -1)] = t
                        frame_track_map[frame_num] = tracks_in_frame

                    # Direction string to unit-vector mapping for gaze_direction
                    direction_vectors = {
                        "LEFT": (-1.0, 0.0),
                        "RIGHT": (1.0, 0.0),
                        "UP": (0.0, -1.0),
                        "DOWN": (0.0, 1.0),
                        "CENTER": (0.0, 0.0),
                    }

                    for ev in events_missing_origin:
                        # Find the person's bbox at the event's start_frame
                        frame_tracks = frame_track_map.get(ev.start_frame, {})
                        track_info = frame_tracks.get(ev.track_id)
                        if track_info:
                            bbox = track_info.get("bbox")
                            if bbox and len(bbox) == 4:
                                x1, y1, x2, y2 = bbox
                                # Use top-center of bbox as head/gaze origin
                                head_x = int((x1 + x2) / 2)
                                head_y = int(y1 + (y2 - y1) * 0.15)  # ~15% from top ≈ head level
                                ev.gaze_origin = (head_x, head_y)

                                # Derive gaze_direction from attention_direction
                                dir_str = (ev.attention_direction or "UNKNOWN").upper()
                                ev.gaze_direction = direction_vectors.get(dir_str, (0.0, 0.0))

                    backfilled = sum(1 for e in events_missing_origin if e.gaze_origin)
                    self.logger.info(
                        f"Backfilled gaze_origin for {backfilled}/{len(events_missing_origin)} "
                        f"events from Phase 2 tracking data"
                    )
                except Exception as exc:
                    self.logger.warning(f"Could not backfill gaze_origin from Phase 2 tracks: {exc}")

        # 3. Compute shelf engagement metrics
        shelves_config = shelf_regions or [
            {"id": r.id, "name": r.name, "type": r.type} for r in self.shelf_analyzer.regions.values()
        ]
        shelf_metrics = compute_shelf_metrics(
            events=events,
            configured_shelves=shelves_config,
            zone_dwell_map=zone_dwell_map,
            zone_visitor_map=zone_visitor_map,
            store_id=store_id,
            camera_id=camera_id,
        )

        # 4. Compute product metrics
        product_metrics = compute_product_metrics(
            events=events,
            configured_products=product_mappings,
            is_spatial_mapping_active=self.product_detector.is_configured,
        )

        # 5. Quality statistics
        total_ev_count = len(events)
        valid_ev = sum(1 for e in events if e.confidence >= self.confidence_threshold)
        avg_conf = (sum(e.confidence for e in events) / total_ev_count) if total_ev_count > 0 else 0.0

        quality = AttentionQualityMetrics(
            total_frames_analyzed=total_ev_count * 15,
            total_face_crops_attempted=total_ev_count,
            valid_face_detections=valid_ev,
            low_confidence_faces=total_ev_count - valid_ev,
            face_detection_rate=(valid_ev / total_ev_count) if total_ev_count > 0 else 1.0,
            average_pose_confidence=avg_conf,
        )

        # 6. Summary aggregation
        summary = self.aggregator.aggregate_all(
            events=events,
            shelves=shelf_metrics,
            products=product_metrics,
            quality=quality,
            total_dwell_sec=total_dwell_sec,
        )

        # 7. Generate reports
        job_meta = {
            "job_directory": str(job_output_dir),
            "store_id": store_id,
            "camera_id": camera_id,
        }
        report_data = self.report_generator.generate_json_report(
            summary=summary,
            shelves=shelf_metrics,
            products=product_metrics,
            events=events,
            quality=quality,
            job_metadata=job_meta,
        )

        # Save reports under job_output_dir / "module4"
        m4_dir = job_output_dir / "module4"

        # Generate Heatmap BEFORE writing reports so heatmap data is included in JSON
        heatmap_path = m4_dir / "attention_heatmap.png"
        self.heatmap_generator.render_heatmap_image(events, heatmap_path)
        report_data["heatmap"] = self.heatmap_generator.generate_heatmap_data(events)

        self.report_generator.write_reports(report_data, m4_dir)

        return report_data

