"""
Attention Analysis — Plot Generator
=======================================
Generates matplotlib visualizations for Phase 5 attention analytics.
All charts are clearly labeled as estimated attention values.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ai.attention_analysis.attention_tracker import AttentionEvent
# pyrefly: ignore [missing-import]
from ai.attention_analysis.report import TargetAttentionSummary
from ai.logger import setup_logger
from ai.utils import ensure_directory


class AttentionPlotGenerator:
    """Generates Phase 5 attention analysis plots."""

    def __init__(self, plots_dir: Path, logger: Optional[logging.Logger] = None):
        self.plots_dir = plots_dir
        self.logger = logger or setup_logger("attention_plots")
        ensure_directory(self.plots_dir)

    def generate_all(
        self,
        events: List[AttentionEvent],
        target_summaries: List[TargetAttentionSummary],
    ) -> List[Path]:
        """Generate all Phase 5 plots. Returns list of created file paths."""
        paths = []
        paths.append(self._plot_duration_by_target(target_summaries))
        paths.append(self._plot_events_by_target(target_summaries))
        paths.append(self._plot_avg_duration_by_target(target_summaries))
        paths.append(self._plot_direction_distribution(events))
        paths.append(self._plot_unknown_percentage(events))
        self.logger.info(f"Attention plots generated: {len(paths)}")
        return [p for p in paths if p is not None]

    def _plot_duration_by_target(self, summaries: List[TargetAttentionSummary]) -> Optional[Path]:
        active = [s for s in summaries if s.total_attention_sec > 0]
        if not active:
            return None
        path = self.plots_dir / "attention_duration_by_target.png"
        names = [s.target_name for s in active]
        values = [s.total_attention_sec for s in active]
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(names, values, color="#2196F3", edgecolor="#1565C0")
        ax.set_xlabel("Total Estimated Attention (seconds)")
        ax.set_title("Estimated Attention Duration by Target")
        ax.invert_yaxis()
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}s", va="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path

    def _plot_events_by_target(self, summaries: List[TargetAttentionSummary]) -> Optional[Path]:
        active = [s for s in summaries if s.attention_event_count > 0]
        if not active:
            return None
        path = self.plots_dir / "attention_events_by_target.png"
        names = [s.target_name for s in active]
        values = [s.attention_event_count for s in active]
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(names, values, color="#4CAF50", edgecolor="#2E7D32")
        ax.set_xlabel("Number of Attention Events")
        ax.set_title("Estimated Attention Events by Target")
        ax.invert_yaxis()
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path

    def _plot_avg_duration_by_target(self, summaries: List[TargetAttentionSummary]) -> Optional[Path]:
        active = [s for s in summaries if s.average_attention_sec > 0]
        if not active:
            return None
        path = self.plots_dir / "avg_attention_duration_by_target.png"
        names = [s.target_name for s in active]
        values = [s.average_attention_sec for s in active]
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(names, values, color="#FF9800", edgecolor="#E65100")
        ax.set_xlabel("Average Estimated Attention (seconds)")
        ax.set_title("Average Estimated Attention Duration by Target")
        ax.invert_yaxis()
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}s", va="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path

    def _plot_direction_distribution(self, events: List[AttentionEvent]) -> Optional[Path]:
        if not events:
            return None
        path = self.plots_dir / "attention_direction_distribution.png"
        counts = Counter(e.attention_direction for e in events)
        labels = list(counts.keys())
        values = list(counts.values())
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0", "#607D8B"]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(labels, values, color=colors[:len(labels)], edgecolor="#333")
        ax.set_xlabel("Estimated Attention Direction")
        ax.set_ylabel("Event Count")
        ax.set_title("Estimated Attention Direction Distribution")
        for i, (lbl, val) in enumerate(zip(labels, values)):
            ax.text(i, val + 0.3, str(val), ha="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path

    def _plot_unknown_percentage(self, events: List[AttentionEvent]) -> Optional[Path]:
        if not events:
            return None
        path = self.plots_dir / "unknown_confidence_percentage.png"
        total = len(events)
        unknown = sum(1 for e in events if e.attention_direction == "UNKNOWN")
        known = total - unknown
        fig, ax = plt.subplots(figsize=(6, 6))
        sizes = [known, unknown]
        labels = [f"Valid ({known})", f"Unknown/Low-Conf ({unknown})"]
        colors = ["#4CAF50", "#FF9800"]
        ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%",
               startangle=90, textprops={"fontsize": 10})
        ax.set_title("Estimated Attention: Valid vs Unknown")
        plt.tight_layout()
        fig.savefig(str(path), dpi=150)
        plt.close(fig)
        return path
