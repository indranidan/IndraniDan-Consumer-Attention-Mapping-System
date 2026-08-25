import pytest
import numpy as np
from ai.attention_analysis.heatmap_engine import (
    normalize_camera_coords,
    merge_multi_camera_points,
    compute_density_matrix,
    density_matrix_to_json,
)

def test_normalize_camera_coords():
    points = [
        {"x": 640, "y": 360, "weight": 2.0},
        {"x": 1280, "y": 720},
        {"x": 0, "y": 0}
    ]
    normalized = normalize_camera_coords(points, 1280, 720)
    
    assert len(normalized) == 3
    assert normalized[0]["nx"] == 0.5
    assert normalized[0]["ny"] == 0.5
    assert normalized[0]["weight"] == 2.0
    
    assert normalized[1]["nx"] == 1.0
    assert normalized[1]["ny"] == 1.0
    assert normalized[1]["weight"] == 1.0
    
    assert normalized[2]["nx"] == 0.0
    assert normalized[2]["ny"] == 0.0

def test_merge_multi_camera_points():
    datasets = [
        {
            "camera_width": 1000,
            "camera_height": 1000,
            "points": [{"x": 500, "y": 500}]
        },
        {
            "camera_width": 200,
            "camera_height": 200,
            "points": [{"x": 100, "y": 100, "weight": 3.0}]
        }
    ]
    merged = merge_multi_camera_points(datasets)
    assert len(merged) == 2
    assert merged[0]["nx"] == 0.5
    assert merged[0]["ny"] == 0.5
    assert merged[1]["nx"] == 0.5
    assert merged[1]["ny"] == 0.5
    assert merged[1]["weight"] == 3.0

def test_compute_density_matrix():
    normalized = [
        {"nx": 0.5, "ny": 0.5, "weight": 1.0},
        {"nx": 0.5, "ny": 0.5, "weight": 2.0}
    ]
    matrix = compute_density_matrix(normalized, grid_width=100, grid_height=100, sigma=2.0)
    
    assert matrix.shape == (100, 100)
    assert np.max(matrix) > 0
    # Peak should be around the center (50, 50)
    cy, cx = np.unravel_index(np.argmax(matrix, axis=None), matrix.shape)
    assert 48 <= cx <= 52
    assert 48 <= cy <= 52

def test_density_matrix_to_json():
    matrix = np.zeros((10, 10), dtype=np.float32)
    matrix[5, 5] = 10.0
    matrix[1, 1] = 2.0
    
    grid = density_matrix_to_json(matrix, threshold=0.1)
    assert grid["grid_width"] == 10
    assert grid["grid_height"] == 10
    assert grid["max_intensity"] == 10.0
    assert len(grid["cells"]) == 2
    
    # 10/10 = 1.0, 2/10 = 0.2
    cells = sorted(grid["cells"], key=lambda c: c["intensity"], reverse=True)
    assert cells[0]["x"] == 5
    assert cells[0]["y"] == 5
    assert cells[0]["intensity"] == 1.0
    
    assert cells[1]["x"] == 1
    assert cells[1]["y"] == 1
    assert cells[1]["intensity"] == 0.2
