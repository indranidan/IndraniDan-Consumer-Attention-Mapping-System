"""
Dwell-Time Analysis — Plot Generator
=======================================
Generates matplotlib-based analytical visualizations for dwell-time data:
  - Average dwell time by zone
  - Total dwell time by zone
  - Zone visit count
  - Dwell-time distribution histogram
All charts include clear titles, axis labels, units, and value annotations.
"""

import logging
from pathlib import Path
from typing import List, Optional

from ai.logger import setup_logger
from ai.dwell_time_analysis.dwell_aggregator import (
    DwellDistribution,
    ZoneDwellSummary,
)
from ai.utils import ensure_directory


class DwellPlotGenerator:
    """Generates Phase 4 dwell-time visualizations."""

    def __init__(self, plots_dir: Path, logger: Optional[logging.Logger] = None):
        self.plots_dir = ensure_directory(plots_dir)
        self.logger = logger or setup_logger("dwell_plots")

    def generate_all(
        self,
        zone_summaries: List[ZoneDwellSummary],
        distribution: DwellDistribution,
    ) -> List[Path]:
        """
        Generate all Phase 4 plots.

        Returns
        -------
        List[Path]
            Paths to all generated plot files.
        """
        self.logger.info("Generating dwell-time plots...")

        generated = []

        if zone_summaries:
            p1 = self._plot_avg_dwell_by_zone(zone_summaries)
            if p1:
                generated.append(p1)

            p2 = self._plot_total_dwell_by_zone(zone_summaries)
            if p2:
                generated.append(p2)

            p3 = self._plot_visit_count_by_zone(zone_summaries)
            if p3:
                generated.append(p3)

        if distribution and distribution.buckets:
            p4 = self._plot_dwell_distribution(distribution)
            if p4:
                generated.append(p4)

        self.logger.info(f"Generated {len(generated)} dwell-time plots")
        return generated

    def _plot_avg_dwell_by_zone(self, summaries: List[ZoneDwellSummary]) -> Optional[Path]:
        """Generate average dwell time by zone bar chart."""
        try:
            # pyrefly: ignore [missing-import]
            import matplotlib
            matplotlib.use("Agg")
            # pyrefly: ignore [missing-import]
            import matplotlib.pyplot as plt

            zones_with_data = [s for s in summaries if s.total_visits > 0]
            if not zones_with_data:
                self.logger.warning("No zones with dwell data — skipping avg dwell plot")
                return None

            names = [s.zone_name for s in zones_with_data]
            values = [s.average_dwell_seconds for s in zones_with_data]

            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(names, values, color="#4C9AFF", edgecolor="#2D6EC4", linewidth=1.2)

            # Value annotations
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{val:.1f}s", ha="center", va="bottom", fontsize=10, fontweight="bold",
                )

            ax.set_title("Average Dwell Time by Zone", fontsize=14, fontweight="bold", pad=15)
            ax.set_xlabel("Zone", fontsize=12)
            ax.set_ylabel("Average Dwell Time (seconds)", fontsize=12)
            ax.grid(axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()

            path = self.plots_dir / "avg_dwell_by_zone.png"
            fig.savefig(str(path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            self.logger.info(f"Saved: {path}")
            return path

        except ImportError:
            self.logger.warning("matplotlib not available — skipping avg dwell plot")
            return None
        except Exception as exc:
            self.logger.error(f"Failed to generate avg dwell plot: {exc}")
            return None

    def _plot_total_dwell_by_zone(self, summaries: List[ZoneDwellSummary]) -> Optional[Path]:
        """Generate total dwell time by zone bar chart."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            zones_with_data = [s for s in summaries if s.total_dwell_seconds > 0]
            if not zones_with_data:
                self.logger.warning("No zones with dwell data — skipping total dwell plot")
                return None

            names = [s.zone_name for s in zones_with_data]
            values = [s.total_dwell_seconds for s in zones_with_data]

            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(names, values, color="#36B37E", edgecolor="#1E8A5E", linewidth=1.2)

            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{val:.1f}s", ha="center", va="bottom", fontsize=10, fontweight="bold",
                )

            ax.set_title("Total Dwell Time by Zone", fontsize=14, fontweight="bold", pad=15)
            ax.set_xlabel("Zone", fontsize=12)
            ax.set_ylabel("Total Dwell Time (seconds)", fontsize=12)
            ax.grid(axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()

            path = self.plots_dir / "total_dwell_by_zone.png"
            fig.savefig(str(path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            self.logger.info(f"Saved: {path}")
            return path

        except ImportError:
            self.logger.warning("matplotlib not available — skipping total dwell plot")
            return None
        except Exception as exc:
            self.logger.error(f"Failed to generate total dwell plot: {exc}")
            return None

    def _plot_visit_count_by_zone(self, summaries: List[ZoneDwellSummary]) -> Optional[Path]:
        """Generate zone visit count bar chart."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            zones_with_data = [s for s in summaries if s.total_visits > 0]
            if not zones_with_data:
                self.logger.warning("No zones with visits — skipping visit count plot")
                return None

            names = [s.zone_name for s in zones_with_data]
            completed = [s.completed_visits for s in zones_with_data]
            track_lost = [s.track_lost_visits for s in zones_with_data]

            fig, ax = plt.subplots(figsize=(10, 6))

            bars_completed = ax.bar(names, completed, color="#6554C0", edgecolor="#4C3DA8",
                                     linewidth=1.2, label="Completed")
            bars_lost = ax.bar(names, track_lost, bottom=completed, color="#FF8B00",
                               edgecolor="#CC7000", linewidth=1.2, label="Track Lost")

            # Total annotations
            for i, (c, tl) in enumerate(zip(completed, track_lost)):
                total = c + tl
                ax.text(i, total + 0.3, str(total), ha="center", va="bottom",
                        fontsize=10, fontweight="bold")

            ax.set_title("Zone Visit Count", fontsize=14, fontweight="bold", pad=15)
            ax.set_xlabel("Zone", fontsize=12)
            ax.set_ylabel("Number of Visits", fontsize=12)
            ax.legend(loc="upper right")
            ax.grid(axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()

            path = self.plots_dir / "visit_count_by_zone.png"
            fig.savefig(str(path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            self.logger.info(f"Saved: {path}")
            return path

        except ImportError:
            self.logger.warning("matplotlib not available — skipping visit count plot")
            return None
        except Exception as exc:
            self.logger.error(f"Failed to generate visit count plot: {exc}")
            return None

    def _plot_dwell_distribution(self, distribution: DwellDistribution) -> Optional[Path]:
        """Generate dwell-time distribution histogram."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            if not distribution.buckets:
                return None

            labels = [b.label for b in distribution.buckets]
            counts = [b.visit_count for b in distribution.buckets]

            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(labels, counts, color="#FF5630", edgecolor="#CC4526", linewidth=1.2)

            for bar, val in zip(bars, counts):
                if val > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                        str(val), ha="center", va="bottom", fontsize=10, fontweight="bold",
                    )

            ax.set_title("Dwell-Time Distribution", fontsize=14, fontweight="bold", pad=15)
            ax.set_xlabel("Dwell Duration", fontsize=12)
            ax.set_ylabel("Number of Zone Visits", fontsize=12)
            ax.grid(axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()

            path = self.plots_dir / "dwell_distribution.png"
            fig.savefig(str(path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            self.logger.info(f"Saved: {path}")
            return path

        except ImportError:
            self.logger.warning("matplotlib not available — skipping distribution plot")
            return None
        except Exception as exc:
            self.logger.error(f"Failed to generate distribution plot: {exc}")
            return None
