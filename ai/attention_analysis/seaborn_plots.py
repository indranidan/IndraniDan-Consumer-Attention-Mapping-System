"""
Attention & Behavior Analysis — Seaborn Statistical Plot Generator
===================================================================
Generates high-resolution statistical visualizations using Seaborn & Matplotlib:
  - Markov Zone Transition Probability Heatmaps
  - Product-to-Shelf Engagement Correlation Matrices
  - Temporal Zone Traffic & Dwell Intensity Maps
"""

import logging
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from ai.logger import setup_logger
from ai.utils import ensure_directory

logger = setup_logger("seaborn_plots")


class SeabornPlotGenerator:
    """Generates advanced statistical heatmaps using Seaborn for executive reporting."""

    def __init__(self, output_dir: Path):
        self.output_dir = ensure_directory(output_dir)

    def generate_zone_transition_heatmap(
        self,
        matrix: np.ndarray,
        zone_names: List[str],
        filename: str = "zone_transition_heatmap.png",
    ) -> Path:
        """
        Generate Markov zone-to-zone transition probability heatmap matrix.
        """
        out_path = self.output_dir / filename
        plt.figure(figsize=(max(8, len(zone_names) * 1.4), max(6, len(zone_names) * 1.2)), dpi=200)

        # Apply stylish theme
        sns.set_theme(style="white")
        cmap = sns.diverging_palette(220, 20, as_cmap=True)

        ax = sns.heatmap(
            matrix,
            annot=True,
            fmt=".1%",
            cmap="Blues",
            xticklabels=zone_names,
            yticklabels=zone_names,
            cbar_kws={"label": "Transition Probability"},
            linewidths=1.0,
            linecolor="#e2e8f0",
            square=True,
        )

        ax.set_title("Zone-to-Zone Shopper Navigation Transition Matrix", fontsize=13, weight="bold", pad=14)
        ax.set_xlabel("Destination Zone (To)", fontsize=11, weight="bold", labelpad=8)
        ax.set_ylabel("Origin Zone (From)", fontsize=11, weight="bold", labelpad=8)

        plt.tight_layout()
        plt.savefig(str(out_path), bbox_inches="tight")
        plt.close()
        logger.info(f"Generated zone transition heatmap at {out_path}")
        return out_path

    def generate_product_engagement_matrix(
        self,
        engagement_data: np.ndarray,
        product_names: List[str],
        shelf_names: List[str],
        filename: str = "product_shelf_engagement_heatmap.png",
    ) -> Path:
        """
        Generate Shelf vs Product interaction intensity heatmap.
        """
        out_path = self.output_dir / filename
        plt.figure(figsize=(max(9, len(shelf_names) * 1.5), max(7, len(product_names) * 0.8)), dpi=200)

        sns.set_theme(style="whitegrid")
        ax = sns.heatmap(
            engagement_data,
            annot=True,
            fmt=".1f",
            cmap="YlGnBu",
            xticklabels=shelf_names,
            yticklabels=product_names,
            cbar_kws={"label": "Attention & Pickup Score (0 - 100)"},
            linewidths=0.8,
            linecolor="#cbd5e1",
        )

        ax.set_title("Product Attention & Consideration Score by Shelf", fontsize=13, weight="bold", pad=14)
        ax.set_xlabel("Shelf Fixture / Zone", fontsize=11, weight="bold", labelpad=8)
        ax.set_ylabel("Product / SKU", fontsize=11, weight="bold", labelpad=8)

        plt.tight_layout()
        plt.savefig(str(out_path), bbox_inches="tight")
        plt.close()
        logger.info(f"Generated product engagement heatmap at {out_path}")
        return out_path
