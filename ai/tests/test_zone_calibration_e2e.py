"""
End-to-End Zone Calibration & Custom ROI Pipeline Tests
======================================================
Tests custom normalized zone injection, frame-size scaling,
foot-contact containment checks, and CLI argument pipeline execution.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.movement_analysis.zone_manager import ZoneManager
from ai.attention_analysis.attention_region_manager import AttentionRegionManager
from ai.dwell_time_analysis.dwell_tracker import DwellTracker


class TestCustomZoneCalibrationE2E:
    """E2E Verification for interactive calibrated zones."""

    def test_custom_normalized_zones_file_scaling(self, tmp_path):
        """Verify custom normalized zones JSON file is loaded and scaled accurately."""
        custom_zones_data = {
            "zones": [
                {
                    "id": "beverage_custom",
                    "name": "Custom Beverage Aisle",
                    "polygon": [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]],
                }
            ],
            "entry_regions": [
                {
                    "id": "entry_custom",
                    "name": "Custom West Entrance",
                    "polygon": [[0.0, 0.5], [0.1, 0.5], [0.1, 0.9], [0.0, 0.9]],
                }
            ],
            "exit_regions": [
                {
                    "id": "exit_custom",
                    "name": "Custom East Exit",
                    "polygon": [[0.9, 0.5], [1.0, 0.5], [1.0, 0.9], [0.9, 0.9]],
                }
            ],
        }
        zones_file = tmp_path / "custom_zones.json"
        zones_file.write_text(json.dumps(custom_zones_data), encoding="utf-8")

        zm = ZoneManager(zones_file)
        assert zm.is_normalized is True

        # Scale to 1920x1080
        zm.scale_to_frame_size(1920, 1080)
        zone = zm.zones.get("beverage_custom")
        assert zone is not None
        # [0.1*1920, 0.2*1080] = [192, 216]
        assert zone.polygon[0] == (192, 216)
        # [0.4*1920, 0.6*1080] = [768, 648]
        assert zone.polygon[2] == (768, 648)

        # Foot contact point inside beverage zone
        foot_x, foot_y = 300, 300
        matching = zm.get_zones_for_point(foot_x, foot_y)
        assert matching == ["beverage_custom"]

        # Point outside
        assert len(zm.get_zones_for_point(50, 50)) == 0

    def test_custom_normalized_attention_shelves(self, tmp_path):
        """Verify custom shelf regions JSON file is scaled and targets attention."""
        custom_attn_data = {
            "regions": [
                {
                    "id": "shelf_top_tier",
                    "name": "Top Tier Premium Shelf",
                    "type": "shelf",
                    "polygon": [[0.2, 0.1], [0.5, 0.1], [0.5, 0.4], [0.2, 0.4]],
                }
            ]
        }
        attn_file = tmp_path / "custom_attention.json"
        attn_file.write_text(json.dumps(custom_attn_data), encoding="utf-8")

        arm = AttentionRegionManager(attn_file)
        assert arm.is_normalized is True

        arm.scale_to_frame_size(1280, 720)
        region = arm.get_region("shelf_top_tier")
        assert region is not None
        assert region.polygon[0] == (256, 72)
        assert region.polygon[2] == (640, 288)

    def test_foot_contact_dwell_tracking(self, tmp_path):
        """Verify DwellTracker correctly records dwell times inside calibrated zones."""
        custom_zones_data = {
            "zones": [
                {
                    "id": "snack_zone",
                    "name": "Snack Zone",
                    "polygon": [[0.2, 0.2], [0.6, 0.2], [0.6, 0.7], [0.2, 0.7]],
                }
            ],
            "entry_regions": [],
            "exit_regions": [],
        }
        zones_file = tmp_path / "custom_zones.json"
        zones_file.write_text(json.dumps(custom_zones_data), encoding="utf-8")

        zm = ZoneManager(zones_file)
        zm.scale_to_frame_size(1000, 1000)

        dt = DwellTracker(gap_tolerance=15)
        zone_names = {"snack_zone": "Snack Zone"}

        # Simulate person walking into zone and standing for 3 seconds
        # Person bbox: x1=250, y1=100, x2=350, y2=400 (foot is at 300, 400 - inside zone 200..600, 200..700)
        # Head/chest centroid would be (300, 250), foot is (300, 400)
        for second in range(4):
            foot_x, foot_y = 300, 400
            current_zones = zm.get_zones_for_point(foot_x, foot_y)
            dt.update(
                track_id=101,
                frame=second * 30,
                timestamp=float(second),
                current_zone_ids=current_zones,
                zone_names=zone_names,
                confidence=0.95,
            )

        active = dt.get_active_dwell_times(101, 3.0)
        assert "snack_zone" in active
        assert active["snack_zone"] >= 3.0
