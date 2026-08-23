"""
Unit Tests — Seaborn Statistical Visualizations
================================================
Tests generation of Markov transition heatmaps and product engagement matrices.
"""

import sys
import tempfile
from pathlib import Path
import numpy as np

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.attention_analysis.seaborn_plots import SeabornPlotGenerator


def test_generate_zone_transition_heatmap():
    with tempfile.TemporaryDirectory() as tmp_dir:
        gen = SeabornPlotGenerator(output_dir=Path(tmp_dir))
        matrix = np.array([
            [0.6, 0.3, 0.1],
            [0.2, 0.5, 0.3],
            [0.1, 0.4, 0.5],
        ])
        zones = ["Entrance", "Aisle 1", "Checkout"]

        out_path = gen.generate_zone_transition_heatmap(matrix, zones)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000


def test_generate_product_engagement_matrix():
    with tempfile.TemporaryDirectory() as tmp_dir:
        gen = SeabornPlotGenerator(output_dir=Path(tmp_dir))
        engagement = np.array([
            [85.5, 42.0],
            [12.3, 91.0],
            [67.8, 33.4],
        ])
        products = ["Organic Milk", "Cereal Box", "Protein Bar"]
        shelves = ["Shelf A (Dairy)", "Shelf B (Snacks)"]

        out_path = gen.generate_product_engagement_matrix(engagement, products, shelves)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000
