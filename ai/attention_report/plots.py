"""
Attention Report — Visualization
====================================
Generates 12 charts for the Phase 6 attention report using matplotlib.
All charts include clear titles, axis labels, units, and legends.
Does NOT generate misleading charts.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.logger import setup_logger
from ai.utils import ensure_directory


class ReportPlotter:
    """Generates all Phase 6 report charts."""

    def __init__(self, plots_dir: Path, logger: Optional[logging.Logger] = None):
        self.plots_dir = ensure_directory(plots_dir)
        self.logger = logger or setup_logger("report_plotter")

    def generate_all(self, report: Dict[str, Any]) -> List[Path]:
        """Generate all 12 charts and return their paths."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            "figure.figsize": (10, 6),
            "figure.dpi": 150,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
        })

        generated = []
        chart_methods = [
            ("01_shopper_traffic_over_time", self._plot_traffic_over_time),
            ("02_visitors_by_zone", self._plot_visitors_by_zone),
            ("03_avg_dwell_by_zone", self._plot_avg_dwell_by_zone),
            ("04_total_dwell_by_zone", self._plot_total_dwell_by_zone),
            ("05_attention_events_by_target", self._plot_attention_events_by_target),
            ("06_total_attention_by_target", self._plot_total_attention_by_target),
            ("07_avg_attention_by_target", self._plot_avg_attention_by_target),
            ("08_attention_direction", self._plot_attention_direction),
            ("09_attention_confidence", self._plot_attention_confidence),
            ("10_dwell_vs_attention", self._plot_dwell_vs_attention),
            ("11_dwell_distribution", self._plot_dwell_distribution),
            ("12_attention_duration_distribution", self._plot_attention_duration_distribution),
        ]

        for name, method in chart_methods:
            try:
                path = method(report, name, plt)
                if path:
                    generated.append(path)
                    self.logger.info(f"  ✓ {name}.png")
            except Exception as exc:
                self.logger.warning(f"  ✗ {name}: {exc}")
            finally:
                plt.close("all")

        return generated

    def _save(self, plt, name: str) -> Path:
        path = self.plots_dir / f"{name}.png"
        plt.tight_layout()
        plt.savefig(path, bbox_inches="tight")
        return path

    def _plot_traffic_over_time(self, report, name, plt) -> Optional[Path]:
        ts = report.get("time_series", {}).get("shopper_traffic_over_time", [])
        if not ts:
            return None
        labels = [p.get("period", "") for p in ts]
        values = [p.get("active_shoppers", 0) for p in ts]
        plt.figure()
        plt.bar(range(len(labels)), values, color="#4A90D9")
        plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
        plt.title("Shopper Traffic Over Time")
        plt.xlabel("Time Period")
        plt.ylabel("Active Shoppers (count)")
        return self._save(plt, name)

    def _plot_visitors_by_zone(self, report, name, plt) -> Optional[Path]:
        zones = report.get("zones", [])
        if not zones:
            return None
        names = [z.get("zone_name", z.get("zone_id")) for z in zones]
        visitors = [z.get("unique_visitors", 0) for z in zones]
        plt.figure()
        bars = plt.barh(names, visitors, color="#5CB85C")
        plt.title("Unique Visitors by Zone")
        plt.xlabel("Unique Visitors (count)")
        plt.ylabel("Zone")
        for bar, v in zip(bars, visitors):
            plt.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     str(v), va="center", fontsize=9)
        return self._save(plt, name)

    def _plot_avg_dwell_by_zone(self, report, name, plt) -> Optional[Path]:
        zones = report.get("zones", [])
        if not zones:
            return None
        names = [z.get("zone_name", z.get("zone_id")) for z in zones]
        values = [z.get("average_dwell_time_sec", 0) or 0 for z in zones]
        plt.figure()
        bars = plt.barh(names, values, color="#F0AD4E")
        plt.title("Average Zone Dwell Time (Observed)")
        plt.xlabel("Average Dwell Time (seconds)")
        plt.ylabel("Zone")
        for bar, v in zip(bars, values):
            plt.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                     f"{v:.2f}s", va="center", fontsize=9)
        return self._save(plt, name)

    def _plot_total_dwell_by_zone(self, report, name, plt) -> Optional[Path]:
        zones = report.get("zones", [])
        if not zones:
            return None
        names = [z.get("zone_name", z.get("zone_id")) for z in zones]
        values = [z.get("total_dwell_time_sec", 0) or 0 for z in zones]
        plt.figure()
        bars = plt.barh(names, values, color="#D9534F")
        plt.title("Total Zone Dwell Time (Observed)")
        plt.xlabel("Total Dwell Time (seconds)")
        plt.ylabel("Zone")
        for bar, v in zip(bars, values):
            plt.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     f"{v:.1f}s", va="center", fontsize=9)
        return self._save(plt, name)

    def _plot_attention_events_by_target(self, report, name, plt) -> Optional[Path]:
        targets = report.get("targets", [])
        if not targets:
            return None
        names = [t.get("target_name", t.get("target_id")) for t in targets]
        counts = [t.get("attention_event_count", 0) for t in targets]
        plt.figure()
        plt.bar(names, counts, color="#5BC0DE")
        plt.title("Attention Events by Target (Estimated)")
        plt.xlabel("Attention Target")
        plt.ylabel("Event Count")
        plt.xticks(rotation=45, ha="right")
        return self._save(plt, name)

    def _plot_total_attention_by_target(self, report, name, plt) -> Optional[Path]:
        targets = report.get("targets", [])
        if not targets:
            return None
        names = [t.get("target_name", t.get("target_id")) for t in targets]
        values = [t.get("total_estimated_attention_duration_sec", 0) or 0 for t in targets]
        plt.figure()
        plt.bar(names, values, color="#9B59B6")
        plt.title("Total Estimated Attention Duration by Target")
        plt.xlabel("Attention Target")
        plt.ylabel("Total Attention Duration (seconds)")
        plt.xticks(rotation=45, ha="right")
        return self._save(plt, name)

    def _plot_avg_attention_by_target(self, report, name, plt) -> Optional[Path]:
        targets = report.get("targets", [])
        if not targets:
            return None
        names = [t.get("target_name", t.get("target_id")) for t in targets]
        values = [t.get("average_attention_duration_sec", 0) or 0 for t in targets]
        plt.figure()
        plt.bar(names, values, color="#E67E22")
        plt.title("Average Estimated Attention Duration by Target")
        plt.xlabel("Attention Target")
        plt.ylabel("Average Attention Duration (seconds)")
        plt.xticks(rotation=45, ha="right")
        return self._save(plt, name)

    def _plot_attention_direction(self, report, name, plt) -> Optional[Path]:
        direction_data = report.get("attention_direction", {}).get("directions", {})
        if not direction_data:
            return None
        labels = list(direction_data.keys())
        counts = [d.get("observation_count", 0) for d in direction_data.values()]
        if sum(counts) == 0:
            return None
        colors = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#95A5A6"]
        plt.figure()
        non_zero = [(l, c, colors[i % len(colors)]) for i, (l, c) in enumerate(zip(labels, counts)) if c > 0]
        if not non_zero:
            return None
        lbl, cnt, clr = zip(*non_zero)
        plt.pie(cnt, labels=lbl, colors=clr, autopct="%1.1f%%", startangle=140)
        plt.title("Estimated Attention Direction Distribution")
        return self._save(plt, name)

    def _plot_attention_confidence(self, report, name, plt) -> Optional[Path]:
        conf = report.get("confidence", {})
        categories = ["High Confidence", "Low Confidence", "Unknown"]
        values = [
            conf.get("high_confidence_observations", 0),
            conf.get("low_confidence_observations", 0),
            conf.get("unknown_observations", 0),
        ]
        if sum(values) == 0:
            return None
        plt.figure()
        colors = ["#27AE60", "#E74C3C", "#95A5A6"]
        plt.bar(categories, values, color=colors)
        plt.title("Attention Confidence Distribution")
        plt.xlabel("Confidence Category")
        plt.ylabel("Observation Count")
        for i, v in enumerate(values):
            plt.text(i, v + 0.5, str(v), ha="center", fontsize=9)
        return self._save(plt, name)

    def _plot_dwell_vs_attention(self, report, name, plt) -> Optional[Path]:
        dva = report.get("dwell_vs_attention", {}).get("zones", [])
        if not dva:
            return None
        import numpy as np
        names = [z.get("zone_name", z.get("zone_id")) for z in dva]
        dwell = [z.get("total_dwell_time_sec", 0) or 0 for z in dva]
        attn = [z.get("total_estimated_attention_time_sec", 0) or 0 for z in dva]
        x = np.arange(len(names))
        width = 0.35
        plt.figure()
        plt.bar(x - width / 2, dwell, width, label="Observed Dwell Time", color="#3498DB")
        plt.bar(x + width / 2, attn, width, label="Estimated Attention Time", color="#E74C3C")
        plt.xticks(x, names, rotation=45, ha="right")
        plt.title("Observed Dwell Time vs Estimated Attention Time")
        plt.xlabel("Zone")
        plt.ylabel("Time (seconds)")
        plt.legend()
        return self._save(plt, name)

    def _plot_dwell_distribution(self, report, name, plt) -> Optional[Path]:
        # Use dwell_distribution from Phase 4 data
        dist = report.get("_dwell_distribution", [])
        if not dist:
            return None
        labels = [b.get("label", "") for b in dist]
        counts = [b.get("visit_count", 0) for b in dist]
        plt.figure()
        plt.bar(labels, counts, color="#1ABC9C")
        plt.title("Dwell-Time Distribution")
        plt.xlabel("Duration Bucket")
        plt.ylabel("Visit Count")
        for i, v in enumerate(counts):
            plt.text(i, v + 0.3, str(v), ha="center", fontsize=9)
        return self._save(plt, name)

    def _plot_attention_duration_distribution(self, report, name, plt) -> Optional[Path]:
        events = report.get("_attention_events_raw", [])
        durations = [e.get("duration_seconds", 0) for e in events
                     if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0]
        if not durations:
            return None
        plt.figure()
        plt.hist(durations, bins=min(20, len(durations)), color="#8E44AD", edgecolor="white")
        plt.title("Estimated Attention Duration Distribution")
        plt.xlabel("Duration (seconds)")
        plt.ylabel("Event Count")
        return self._save(plt, name)
