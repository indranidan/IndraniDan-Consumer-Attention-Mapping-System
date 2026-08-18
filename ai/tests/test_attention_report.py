"""
Module 3 Phase 6 — Attention Report Tests
=============================================
Unit tests using synthetic JSON fixtures. No video required.
"""

import json
import math
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai.attention_report.config import ReportConfig
from ai.attention_report.input_validator import InputValidator
from ai.attention_report.data_loader import ReportDataLoader, ReportData
from ai.attention_report.aggregator import ReportAggregator, _safe_div


# ── Fixtures ─────────────────────────────────────────────────────

def _make_sessions():
    return {"generated_at": "2026-01-01", "sessions": [
        {"session_id": "s1", "tracking_id": 1, "start_time": 0.0, "end_time": 5.0,
         "entry_time": 0.0, "exit_time": 5.0, "status": "completed",
         "zones_visited": ["zone_1"], "zone_transitions": [], "frames_tracked": 100,
         "average_confidence": 0.8, "journey": []},
        {"session_id": "s2", "tracking_id": 2, "start_time": 1.0, "end_time": 3.0,
         "entry_time": 1.0, "exit_time": None, "status": "track_lost",
         "zones_visited": ["zone_1", "zone_2"], "zone_transitions": [], "frames_tracked": 50,
         "average_confidence": 0.7, "journey": []},
    ]}

def _make_traffic():
    return {"generated_at": "2026-01-01", "total_unique_shoppers": 2, "total_entries": 2,
            "total_exits": 1, "total_track_lost": 1, "completed_sessions": 1,
            "track_lost_sessions": 1, "zone_statistics": [
                {"zone_id": "zone_1", "zone_name": "Beverage", "unique_visitors": 2, "total_visits": 3},
                {"zone_id": "zone_2", "zone_name": "Snacks", "unique_visitors": 1, "total_visits": 1},
            ], "traffic_by_time_period": [
                {"period": "00:00-01:00", "start_time": 0, "end_time": 60, "active_shoppers": 2}
            ]}

def _make_zone_visits():
    return {"generated_at": "2026-01-01", "zone_visits": [
        {"zone_id": "zone_1", "zone_name": "Beverage", "entry_time": 0.0, "exit_time": 3.0,
         "duration": 3.0, "tracking_id": 1, "entry_frame": 0, "exit_frame": 90},
        {"zone_id": "zone_1", "zone_name": "Beverage", "entry_time": 1.0, "exit_time": 2.0,
         "duration": 1.0, "tracking_id": 2, "entry_frame": 30, "exit_frame": 60},
        {"zone_id": "zone_2", "zone_name": "Snacks", "entry_time": 2.5, "exit_time": 3.0,
         "duration": 0.5, "tracking_id": 2, "entry_frame": 75, "exit_frame": 90},
    ]}

def _make_dwell_events():
    return {"generated_at": "2026-01-01", "total_events": 3, "events": [
        {"tracking_id": 1, "zone_id": "zone_1", "zone_name": "Beverage", "visit_number": 1,
         "entry_time": 0.0, "exit_time": 3.0, "dwell_seconds": 3.0, "status": "completed",
         "entry_frame": 0, "exit_frame": 90, "frames_observed": 90, "average_confidence": 0.8},
        {"tracking_id": 2, "zone_id": "zone_1", "zone_name": "Beverage", "visit_number": 1,
         "entry_time": 1.0, "exit_time": 2.0, "dwell_seconds": 1.0, "status": "track_lost",
         "entry_frame": 30, "exit_frame": 60, "frames_observed": 30, "average_confidence": 0.7},
        {"tracking_id": 2, "zone_id": "zone_2", "zone_name": "Snacks", "visit_number": 1,
         "entry_time": 2.5, "exit_time": 3.0, "dwell_seconds": 0.5, "status": "track_lost",
         "entry_frame": 75, "exit_frame": 90, "frames_observed": 15, "average_confidence": 0.6},
    ]}

def _make_zone_dwell():
    return {"generated_at": "2026-01-01", "total_zones": 2, "zone_summaries": [
        {"zone_id": "zone_1", "zone_name": "Beverage", "unique_shoppers": 2, "total_visits": 2,
         "completed_visits": 1, "track_lost_visits": 1, "total_dwell_seconds": 4.0,
         "average_dwell_seconds": 2.0, "median_dwell_seconds": 2.0, "min_dwell_seconds": 1.0,
         "max_dwell_seconds": 3.0, "current_active_shoppers": 0},
        {"zone_id": "zone_2", "zone_name": "Snacks", "unique_shoppers": 1, "total_visits": 1,
         "completed_visits": 0, "track_lost_visits": 1, "total_dwell_seconds": 0.5,
         "average_dwell_seconds": 0.5, "median_dwell_seconds": 0.5, "min_dwell_seconds": 0.5,
         "max_dwell_seconds": 0.5, "current_active_shoppers": 0},
    ]}

def _make_shopper_dwell():
    return {"generated_at": "2026-01-01", "total_shoppers": 2, "shopper_summaries": [
        {"tracking_id": 1, "session_duration": 5.0, "session_status": "completed",
         "zones_visited": 1, "total_zone_visits": 1, "total_observed_dwell_seconds": 3.0,
         "average_zone_dwell_seconds": 3.0, "longest_zone_visit_seconds": 3.0,
         "zone_with_longest_dwell": "zone_1", "zone_name_with_longest_dwell": "Beverage"},
        {"tracking_id": 2, "session_duration": 2.0, "session_status": "track_lost",
         "zones_visited": 2, "total_zone_visits": 2, "total_observed_dwell_seconds": 1.5,
         "average_zone_dwell_seconds": 0.75, "longest_zone_visit_seconds": 1.0,
         "zone_with_longest_dwell": "zone_1", "zone_name_with_longest_dwell": "Beverage"},
    ]}

def _make_dwell_dist():
    return {"generated_at": "2026-01-01", "total_visits_counted": 3, "buckets": [
        {"label": "0-10s", "min_seconds": 0, "max_seconds": 10, "visit_count": 3},
        {"label": "10-30s", "min_seconds": 10, "max_seconds": 30, "visit_count": 0},
    ]}

def _make_attn_events():
    return {"generated_at": "2026-01-01", "total_events": 3, "note": "estimated",
            "events": [
        {"tracking_id": 1, "zone_id": "zone_1", "target_type": "shelf", "target_id": "shelf_1",
         "target_name": "Beverage Shelf", "start_time": 0.5, "end_time": 2.5,
         "duration_seconds": 2.0, "attention_direction": "CENTER", "confidence": 0.85,
         "status": "completed", "visit_number": 1, "start_frame": 15, "end_frame": 75},
        {"tracking_id": 1, "zone_id": "zone_1", "target_type": "shelf", "target_id": "shelf_1",
         "target_name": "Beverage Shelf", "start_time": 3.0, "end_time": 4.0,
         "duration_seconds": 1.0, "attention_direction": "LEFT", "confidence": 0.7,
         "status": "completed", "visit_number": 2, "start_frame": 90, "end_frame": 120},
        {"tracking_id": 2, "zone_id": "zone_2", "target_type": "shelf", "target_id": "shelf_2",
         "target_name": "Snacks Shelf", "start_time": 2.5, "end_time": 2.8,
         "duration_seconds": 0.3, "attention_direction": "RIGHT", "confidence": 0.55,
         "status": "track_lost", "visit_number": 1, "start_frame": 75, "end_frame": 84},
    ]}

def _make_shopper_attn():
    return {"generated_at": "2026-01-01", "note": "estimated", "total_shoppers": 2,
            "shoppers": [
        {"tracking_id": 1, "session_duration_sec": 5.0, "attention_event_count": 2,
         "total_estimated_attention_sec": 3.0, "average_attention_sec": 1.5,
         "longest_attention_sec": 2.0, "most_attended_target": "Beverage Shelf",
         "unknown_observation_count": 10, "total_observations": 100},
        {"tracking_id": 2, "session_duration_sec": 2.0, "attention_event_count": 1,
         "total_estimated_attention_sec": 0.3, "average_attention_sec": 0.3,
         "longest_attention_sec": 0.3, "most_attended_target": "Snacks Shelf",
         "unknown_observation_count": 40, "total_observations": 50},
    ]}

def _make_target_attn():
    return {"generated_at": "2026-01-01", "note": "estimated", "total_targets": 2,
            "targets": [
        {"target_id": "shelf_1", "target_name": "Beverage Shelf", "target_type": "shelf",
         "unique_shoppers": 1, "attention_event_count": 2, "total_attention_sec": 3.0,
         "average_attention_sec": 1.5, "maximum_attention_sec": 2.0},
        {"target_id": "shelf_2", "target_name": "Snacks Shelf", "target_type": "shelf",
         "unique_shoppers": 1, "attention_event_count": 1, "total_attention_sec": 0.3,
         "average_attention_sec": 0.3, "maximum_attention_sec": 0.3},
    ]}


def _write_all_fixtures(base: Path):
    """Write all fixture files to a temp directory."""
    p3 = base / "phase3"
    p4 = base / "phase4"
    p5 = base / "phase5"
    for d in [p3, p4, p5]:
        d.mkdir(parents=True, exist_ok=True)

    files = {
        p3 / "sessions.json": _make_sessions(),
        p3 / "traffic_summary.json": _make_traffic(),
        p3 / "zone_visits.json": _make_zone_visits(),
        p3 / "paths.json": {"generated_at": "2026-01-01", "paths": []},
        p4 / "dwell_events.json": _make_dwell_events(),
        p4 / "zone_dwell_summary.json": _make_zone_dwell(),
        p4 / "shopper_dwell_summary.json": _make_shopper_dwell(),
        p4 / "dwell_distribution.json": _make_dwell_dist(),
        p5 / "attention_events.json": _make_attn_events(),
        p5 / "shopper_attention_summary.json": _make_shopper_attn(),
        p5 / "target_attention_summary.json": _make_target_attn(),
    }
    for path, data in files.items():
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p3, p4, p5


def _make_config(tmp_path, p3, p4, p5):
    out = tmp_path / "output"
    out.mkdir(exist_ok=True)
    return ReportConfig(
        phase3_output_path=p3, phase4_output_path=p4, phase5_output_path=p5,
        phase6_output_path=out, reports_dir=out / "reports", plots_dir=out / "plots",
        logs_dir=out / "logs", report_version="1.0", device="cpu",
        person_model_path="yolo.pt", attention_confidence_threshold=0.6,
        attention_smoothing_window=5, attention_regions_path=Path("regions.json"),
        zone_config_path=Path("zones.json"), ai_dir=Path("."), project_root=Path("."),
    )


def _load_data(tmp_path):
    p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
    config = _make_config(tmp_path, p3, p4, p5)
    vr = InputValidator(config).validate_all()
    assert vr.is_valid
    return ReportDataLoader(config).load(vr), config


# ── 1. Input Validation Tests ────────────────────────────────────

class TestInputValidation:
    def test_valid_files(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        config = _make_config(tmp_path, p3, p4, p5)
        result = InputValidator(config).validate_all()
        assert result.is_valid

    def test_missing_required_file(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        (p3 / "sessions.json").unlink()
        config = _make_config(tmp_path, p3, p4, p5)
        result = InputValidator(config).validate_all()
        assert not result.is_valid

    def test_invalid_json(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        (p3 / "sessions.json").write_text("{invalid json", encoding="utf-8")
        config = _make_config(tmp_path, p3, p4, p5)
        result = InputValidator(config).validate_all()
        assert not result.is_valid

    def test_missing_optional_file(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        (p3 / "paths.json").unlink()
        config = _make_config(tmp_path, p3, p4, p5)
        result = InputValidator(config).validate_all()
        assert result.is_valid  # Optional file missing is OK

    def test_missing_required_fields(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        (p3 / "traffic_summary.json").write_text('{"foo": "bar"}', encoding="utf-8")
        config = _make_config(tmp_path, p3, p4, p5)
        result = InputValidator(config).validate_all()
        assert not result.is_valid


# ── 2. Shopper Aggregation ───────────────────────────────────────

class TestShopperAggregation:
    def test_shopper_count(self, tmp_path):
        data, _ = _load_data(tmp_path)
        agg = ReportAggregator(data)
        shoppers = agg.compute_shopper_reports()
        assert len(shoppers) == 2

    def test_shopper_fields(self, tmp_path):
        data, _ = _load_data(tmp_path)
        shoppers = ReportAggregator(data).compute_shopper_reports()
        s1 = next(s for s in shoppers if s["tracking_id"] == 1)
        assert s1["session_status"] == "completed"
        assert s1["attention_event_count"] == 2
        assert s1["total_zone_dwell_time_sec"] == 3.0


# ── 3. Zone Aggregation ─────────────────────────────────────────

class TestZoneAggregation:
    def test_zone_count(self, tmp_path):
        data, _ = _load_data(tmp_path)
        zones = ReportAggregator(data).compute_zone_reports()
        assert len(zones) == 2

    def test_zone_dwell_vs_attention_separate(self, tmp_path):
        data, _ = _load_data(tmp_path)
        zones = ReportAggregator(data).compute_zone_reports()
        z1 = next(z for z in zones if z["zone_id"] == "zone_1")
        assert z1["total_dwell_time_sec"] == 4.0
        # Attention only from events in zone_1
        assert z1["attention_event_count"] == 2


# ── 4. Target Aggregation ───────────────────────────────────────

class TestTargetAggregation:
    def test_target_count(self, tmp_path):
        data, _ = _load_data(tmp_path)
        targets = ReportAggregator(data).compute_target_reports()
        assert len(targets) == 2

    def test_repeat_count(self, tmp_path):
        data, _ = _load_data(tmp_path)
        targets = ReportAggregator(data).compute_target_reports()
        t1 = next(t for t in targets if t["target_id"] == "shelf_1")
        assert t1["repeat_attention_count"] == 1  # Shopper 1 visited twice


# ── 5. Direction Aggregation ────────────────────────────────────

class TestDirectionAggregation:
    def test_direction_counts(self, tmp_path):
        data, _ = _load_data(tmp_path)
        direction = ReportAggregator(data).compute_attention_direction()
        dirs = direction["directions"]
        assert dirs["CENTER"]["observation_count"] == 1
        assert dirs["LEFT"]["observation_count"] == 1
        assert dirs["RIGHT"]["observation_count"] == 1


# ── 6. Confidence Aggregation ───────────────────────────────────

class TestConfidenceAggregation:
    def test_confidence_stats(self, tmp_path):
        data, _ = _load_data(tmp_path)
        conf = ReportAggregator(data).compute_attention_confidence()
        assert conf["minimum_confidence"] == 0.55
        assert conf["maximum_confidence"] == 0.85
        assert conf["unknown_observations"] == 50  # 10 + 40


# ── 7. Dwell vs Attention ───────────────────────────────────────

class TestDwellVsAttention:
    def test_ratio_computed(self, tmp_path):
        data, _ = _load_data(tmp_path)
        dva = ReportAggregator(data).compute_dwell_vs_attention()
        zones = dva["zones"]
        z1 = next(z for z in zones if z["zone_id"] == "zone_1")
        assert z1["total_dwell_time_sec"] == 4.0
        assert z1["attention_to_dwell_ratio"] is not None

    def test_division_by_zero(self, tmp_path):
        assert _safe_div(5.0, 0) is None
        assert _safe_div(0, 0) is None


# ── 8. Repeated Attention ───────────────────────────────────────

class TestRepeatedAttention:
    def test_repeated_detected(self, tmp_path):
        data, _ = _load_data(tmp_path)
        ra = ReportAggregator(data).compute_repeated_attention()
        assert ra["total_repeat_attention_count"] == 1
        assert ra["unique_shoppers_with_repeated_attention"] == 1
        assert ra["most_repeatedly_attended_target"] == "Beverage Shelf"


# ── 9. Rankings ──────────────────────────────────────────────────

class TestRankings:
    def test_rankings_generated(self, tmp_path):
        data, _ = _load_data(tmp_path)
        rankings = ReportAggregator(data).compute_rankings()
        assert "top_zones" in rankings
        assert "top_targets" in rankings
        assert len(rankings["top_zones"]["by_unique_visitors"]) == 2


# ── 10. JSON Generation ─────────────────────────────────────────

class TestJsonGeneration:
    def test_valid_json(self, tmp_path):
        from ai.attention_report.json_writer import JsonReportWriter
        data, config = _load_data(tmp_path)
        (config.reports_dir).mkdir(parents=True, exist_ok=True)
        report = ReportAggregator(data).aggregate_all()
        path = JsonReportWriter(config).write(report)
        assert path.exists()
        content = json.loads(path.read_text(encoding="utf-8"))
        assert content["report_version"] == "1.0"
        assert "summary" in content
        assert "limitations" in content

    def test_no_nan_infinity(self, tmp_path):
        from ai.attention_report.json_writer import _sanitize_value
        assert _sanitize_value(float("nan")) is None
        assert _sanitize_value(float("inf")) is None
        assert _sanitize_value(3.14) == 3.14


# ── 11. Markdown Generation ─────────────────────────────────────

class TestMarkdownGeneration:
    def test_all_sections_present(self, tmp_path):
        from ai.attention_report.markdown_writer import MarkdownReportWriter
        data, config = _load_data(tmp_path)
        (config.reports_dir).mkdir(parents=True, exist_ok=True)
        report = ReportAggregator(data).aggregate_all()
        path = MarkdownReportWriter(config).write(report)
        content = path.read_text(encoding="utf-8")
        for i in range(1, 16):
            assert f"## {i}." in content, f"Section {i} missing"
        assert "Limitations" in content


# ── 12. Missing Data Handling ────────────────────────────────────

class TestMissingDataHandling:
    def test_empty_attention_events(self, tmp_path):
        p3, p4, p5 = _write_all_fixtures(tmp_path / "data")
        (p5 / "attention_events.json").write_text(
            json.dumps({"generated_at": "x", "total_events": 0, "note": "n", "events": []}),
            encoding="utf-8",
        )
        config = _make_config(tmp_path, p3, p4, p5)
        vr = InputValidator(config).validate_all()
        data = ReportDataLoader(config).load(vr)
        report = ReportAggregator(data).aggregate_all()
        assert report["summary"]["total_attention_events"] == 0


# ── 13. Division by Zero ────────────────────────────────────────

class TestDivisionByZero:
    def test_safe_div(self):
        assert _safe_div(10, 0) is None
        assert _safe_div(0, 0) is None
        assert _safe_div(10, 5) == 2.0


# ── 14. Empty Dataset ───────────────────────────────────────────

class TestEmptyDataset:
    def test_empty_sessions(self, tmp_path):
        data = ReportData(sessions=[], traffic_summary={"total_unique_shoppers": 0,
            "total_entries": 0, "total_exits": 0, "zone_statistics": []})
        report = ReportAggregator(data).aggregate_all()
        assert report["summary"]["total_unique_shoppers"] == 0
        assert report["summary"]["total_sessions"] == 0
