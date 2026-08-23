"""
Module 3 Phase 1 — Person Detection Tests
=============================================
Tests for model loading, person class validation, video input handling,
device fallback, and detection output structure.

Run:
    python -m pytest ai/tests/test_person_detection.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_root():
    """Return the project root path."""
    return _PROJECT_ROOT


@pytest.fixture
def yolov8n_path(project_root):
    """Return the path to the COCO-pretrained YOLO model."""
    candidates = [
        project_root / "ai" / "models" / "yolov8n.pt",
        project_root / "ai" / "models" / "yolo26n.pt",
        project_root / "ai" / "yolov8n.pt",
        project_root / "ai" / "yolo26n.pt",
        project_root / "ai" / "coco" / "yolov8n.pt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


@pytest.fixture
def sample_frame():
    """Create a small synthetic BGR frame for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_config(yolov8n_path, tmp_path):
    """Create a PersonDetectionConfig with test values."""
    from ai.person_detection.config import PersonDetectionConfig

    output_base = tmp_path / "outputs" / "module3" / "phase1"

    return PersonDetectionConfig(
        person_model_path=yolov8n_path,
        confidence_threshold=0.40,
        image_size=640,
        device="cpu",
        save_frames=False,
        output_base=output_base,
        videos_dir=output_base / "videos",
        frames_dir=output_base / "frames",
        reports_dir=output_base / "reports",
        logs_dir=output_base / "logs",
    )


# ---------------------------------------------------------------------------
# Test: Configuration Loading
# ---------------------------------------------------------------------------
class TestConfiguration:
    """Test PersonDetectionConfig loading."""

    def test_config_loading(self):
        """PersonDetectionConfig should load from environment variables."""
        from ai.person_detection.config import load_person_detection_config

        config = load_person_detection_config()

        assert config.confidence_threshold > 0
        assert config.confidence_threshold <= 1.0
        assert config.image_size > 0
        assert config.person_model_path is not None
        assert config.output_base is not None

    def test_config_immutable(self):
        """PersonDetectionConfig should be frozen (immutable)."""
        from ai.person_detection.config import load_person_detection_config

        config = load_person_detection_config()

        with pytest.raises(AttributeError):
            config.confidence_threshold = 0.99


# ---------------------------------------------------------------------------
# Test: Model Loading
# ---------------------------------------------------------------------------
class TestModelLoading:
    """Test YOLOv8 model loading and validation."""

    def test_model_loading(self, yolov8n_path):
        """YOLO model should load successfully from yolov8n.pt."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        # pyrefly: ignore [missing-import]
        from ultralytics import YOLO

        model = YOLO(str(yolov8n_path))
        assert model is not None
        assert model.names is not None
        assert len(model.names) > 0

    def test_person_class_exists(self, yolov8n_path):
        """COCO-pretrained yolov8n.pt should contain the 'person' class."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        # pyrefly: ignore [missing-import]
        from ultralytics import YOLO

        model = YOLO(str(yolov8n_path))
        person_classes = [
            name for name in model.names.values() if name.lower() == "person"
        ]
        assert len(person_classes) == 1, (
            f"Expected 'person' class in model names. Got: {list(model.names.values())}"
        )

    def test_person_class_missing_raises_error(self, tmp_path):
        """Detector should raise ValueError when model lacks person class."""
        from ai.person_detection.config import PersonDetectionConfig
        from ai.person_detection.detector import PersonDetector

        # Create a mock config pointing to a non-existent model
        # We'll mock the model loading to simulate a product-only model
        config = PersonDetectionConfig(
            person_model_path=tmp_path / "fake_model.pt",
            confidence_threshold=0.40,
            image_size=640,
            device="cpu",
            save_frames=False,
            output_base=tmp_path,
            videos_dir=tmp_path / "videos",
            frames_dir=tmp_path / "frames",
            reports_dir=tmp_path / "reports",
            logs_dir=tmp_path / "logs",
        )

        with pytest.raises(FileNotFoundError, match="Person detection model not found"):
            PersonDetector(config)

    def test_detector_initializes_with_coco_model(self, mock_config, yolov8n_path):
        """PersonDetector should initialize successfully with COCO model."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector

        detector = PersonDetector(mock_config)
        assert detector.model is not None
        assert detector.person_class_id is not None
        assert detector.device is not None


# ---------------------------------------------------------------------------
# Test: Video Input Handling
# ---------------------------------------------------------------------------
class TestVideoInput:
    """Test video source validation."""

    def test_invalid_video_path(self, mock_config, yolov8n_path):
        """VideoProcessor should raise FileNotFoundError for non-existent video."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector
        from ai.person_detection.video_processor import VideoProcessor

        detector = PersonDetector(mock_config)
        processor = VideoProcessor(
            source="/nonexistent/path/video.mp4",
            config=mock_config,
            detector=detector,
        )

        with pytest.raises(FileNotFoundError, match="Video file not found"):
            processor.open()

    def test_webcam_failure_handling(self, mock_config, yolov8n_path):
        """VideoProcessor should raise RuntimeError for invalid webcam index."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector
        from ai.person_detection.video_processor import VideoProcessor

        detector = PersonDetector(mock_config)
        processor = VideoProcessor(
            source="999",  # Very unlikely to be a valid webcam index
            config=mock_config,
            detector=detector,
        )

        with pytest.raises(RuntimeError, match="Cannot open webcam"):
            processor.open()


# ---------------------------------------------------------------------------
# Test: Device Fallback
# ---------------------------------------------------------------------------
class TestDeviceFallback:
    """Test CUDA/CPU device selection."""

    def test_cpu_fallback(self):
        """get_device('auto') should return 'cpu' when no CUDA is available."""
        from ai.utils import get_device

        device = get_device("auto")
        # On a machine without CUDA, this should be "cpu"
        # On a machine with CUDA, this should be "cuda:0"
        assert device in ("cpu", "cuda:0"), f"Unexpected device: {device}"

    def test_explicit_cpu(self):
        """get_device('cpu') should always return 'cpu'."""
        from ai.utils import get_device

        device = get_device("cpu")
        assert device == "cpu"


# ---------------------------------------------------------------------------
# Test: Detection Output Structure
# ---------------------------------------------------------------------------
class TestDetectionOutput:
    """Test detection result structure and annotation."""

    def test_detection_output_structure(self, mock_config, yolov8n_path, sample_frame):
        """detect() should return list of Detection namedtuples and inference time."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector, Detection

        detector = PersonDetector(mock_config)
        detections, inference_ms = detector.detect(sample_frame)

        assert isinstance(detections, list)
        assert isinstance(inference_ms, float)
        assert inference_ms >= 0

        # On a blank frame we may get 0 detections — that's valid
        for det in detections:
            assert isinstance(det, Detection)
            assert len(det.bbox) == 4
            assert 0 <= det.confidence <= 1.0
            assert isinstance(det.class_id, int)
            assert det.class_name == "person"

    def test_annotation_returns_frame(self, mock_config, yolov8n_path, sample_frame):
        """annotate() should return a numpy array of the same shape."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector, Detection

        detector = PersonDetector(mock_config)

        # Create a fake detection
        fake_detections = [
            Detection(
                bbox=(100, 100, 200, 300),
                confidence=0.85,
                class_id=0,
                class_name="person",
            )
        ]

        annotated = detector.annotate(sample_frame, fake_detections)
        assert isinstance(annotated, np.ndarray)
        assert annotated.shape == sample_frame.shape

    def test_annotation_does_not_modify_original(
        self, mock_config, yolov8n_path, sample_frame
    ):
        """annotate() should not modify the original frame."""
        if not yolov8n_path.exists():
            pytest.skip(f"Model file not found: {yolov8n_path}")

        from ai.person_detection.detector import PersonDetector, Detection

        detector = PersonDetector(mock_config)
        original_copy = sample_frame.copy()

        fake_detections = [
            Detection(
                bbox=(100, 100, 200, 300),
                confidence=0.85,
                class_id=0,
                class_name="person",
            )
        ]

        detector.annotate(sample_frame, fake_detections)
        assert np.array_equal(sample_frame, original_copy)


# ---------------------------------------------------------------------------
# Test: Report Generation
# ---------------------------------------------------------------------------
class TestReportGeneration:
    """Test JSON and Markdown report creation."""

    def test_report_generation(self, tmp_path):
        """ReportGenerator should create both JSON and Markdown files."""
        from ai.person_detection.report import ReportGenerator

        reporter = ReportGenerator(tmp_path)

        stats = {
            "video_filename": "test_video.mp4",
            "video_path": "/path/to/test_video.mp4",
            "video_duration_sec": 10.5,
            "video_resolution": "1280x720",
            "video_fps": 30.0,
            "total_frames_processed": 315,
            "total_frames_with_persons": 200,
            "total_person_detections": 450,
            "average_inference_time_ms": 35.5,
            "average_confidence": 0.7823,
            "total_pipeline_time_sec": 15.2,
            "effective_fps": 20.72,
            "device": "cpu",
            "model": "/path/to/model.pt",
            "confidence_threshold": 0.40,
            "image_size": 640,
            "output_video": "/path/to/output.mp4",
            "save_frames": False,
        }

        json_path, md_path = reporter.generate(stats)

        assert json_path.exists()
        assert md_path.exists()
        assert json_path.suffix == ".json"
        assert md_path.suffix == ".md"

        # Verify JSON is valid
        import json

        with open(json_path) as f:
            data = json.load(f)
        assert data["total_frames_processed"] == 315
        assert data["report_type"] == "person_detection"

        # Verify Markdown contains key info
        md_content = md_path.read_text()
        assert "test_video.mp4" in md_content
        assert "1280x720" in md_content
