"""
Test Enhanced Platform Features
===============================
Verifies dashboard analytics aggregations and camera health testing endpoints.
"""

import sys
from pathlib import Path
import uuid
from unittest.mock import MagicMock, patch

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.orm import Session
from app.models.store import Store
from app.models.camera import Camera
from app.models.shelf import Shelf
from app.models.zone import Zone
from app.services.dashboard_service import get_dashboard_analytics_data
from app.services.camera_service import probe_camera_stream


def test_dashboard_analytics_aggregation():
    """Verify get_dashboard_analytics_data aggregates stats across mock entities."""
    mock_db = MagicMock(spec=Session)

    store_id = uuid.uuid4()
    mock_store = MagicMock()
    mock_store.id = store_id
    mock_store.name = "Downtown Flagship"
    mock_store.address = "100 Main St"

    cam_id = uuid.uuid4()
    mock_cam = MagicMock()
    mock_cam.id = cam_id
    mock_cam.name = "Aisle Cam 1"
    mock_cam.store_id = store_id

    mock_shelf = MagicMock()
    mock_shelf.id = uuid.uuid4()
    mock_shelf.name = "Beverages Shelf"
    mock_shelf.store_id = store_id

    mock_db.query.return_value.all.side_effect = [
        [mock_store],     # Stores
        [mock_cam],       # Cameras
        [mock_shelf],     # Shelves
        [],               # Products
        [],               # Completed AIJobs
        [],               # Recent AIJobs
    ]

    with patch("app.repositories.ai_document_repository.AIDocumentRepository.get_module4_analysis_sync", return_value=None), \
         patch("app.repositories.ai_document_repository.AIDocumentRepository.get_module5_analysis_sync", return_value=None):
        data = get_dashboard_analytics_data(mock_db)

    assert "overview" in data
    assert data["overview"]["total_stores"] == 1
    assert data["overview"]["total_cameras"] == 1
    assert "top_shelves" in data
    assert "store_performance" in data
    assert "traffic_trend" in data
    assert len(data["traffic_trend"]) == 7


def test_camera_stream_ping_diagnostics():
    """Verify camera stream connection ping handles online and offline streams safely."""
    mock_db = MagicMock(spec=Session)
    cam_id = uuid.uuid4()
    mock_cam = MagicMock()
    mock_cam.id = cam_id
    mock_cam.camera_source = "rtsp://127.0.0.1:8554/cam1"

    mock_db.query.return_value.filter.return_value.first.return_value = mock_cam

    # 1. Test Online stream mock
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, MagicMock())
    mock_cap.get.side_effect = lambda prop: 1920 if prop == 3 else 1080 if prop == 4 else 30.0

    with patch("cv2.VideoCapture", return_value=mock_cap):
        result_online = probe_camera_stream(mock_db, cam_id)
        assert result_online["camera_id"] == str(cam_id)
        assert result_online["status"] == "ONLINE"
        assert result_online["resolution"] == "1920x1080"
        assert result_online["fps"] == 30.0

    # 2. Test Offline stream mock
    mock_offline_cap = MagicMock()
    mock_offline_cap.isOpened.return_value = False

    with patch("cv2.VideoCapture", return_value=mock_offline_cap):
        result_offline = probe_camera_stream(mock_db, cam_id)
        assert result_offline["camera_id"] == str(cam_id)
        assert result_offline["status"] == "OFFLINE"

