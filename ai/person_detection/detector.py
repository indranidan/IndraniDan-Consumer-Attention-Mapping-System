"""
Person Detection — Detector
==============================
Loads a YOLOv8 model, validates it contains the "person" class,
runs inference on individual frames, and draws annotated bounding boxes.
"""

import logging
import time
from pathlib import Path
from typing import List, NamedTuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

# pyrefly: ignore [missing-import]
from ultralytics import YOLO

from ai.person_detection.config import PersonDetectionConfig
from ai.logger import setup_logger


# ---------------------------------------------------------------------------
# Detection result structure
# ---------------------------------------------------------------------------
class Detection(NamedTuple):
    """Single person detection result."""

    bbox: tuple  # (x1, y1, x2, y2) in pixel coordinates
    confidence: float
    class_id: int
    class_name: str


# ---------------------------------------------------------------------------
# Annotation colours & font settings
# ---------------------------------------------------------------------------
_BOX_COLOR = (0, 255, 0)       # Green bounding box
_TEXT_COLOR = (255, 255, 255)   # White text
_TEXT_BG_COLOR = (0, 255, 0)   # Green text background
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.6
_FONT_THICKNESS = 2
_BOX_THICKNESS = 2


class PersonDetector:
    """
    YOLOv8-based person detector.

    Loads the model, validates it can detect "person",
    and provides inference + annotation methods.
    """

    def __init__(self, config: PersonDetectionConfig, logger: logging.Logger = None):
        """
        Initialize the person detector.

        Parameters
        ----------
        config : PersonDetectionConfig
            Configuration with model path, thresholds, device, etc.
        logger : logging.Logger, optional
            Logger instance. Creates one if not provided.

        Raises
        ------
        FileNotFoundError
            If the model file does not exist.
        ValueError
            If the model does not contain a "person" class.
        RuntimeError
            If the model cannot be loaded.
        """
        self.config = config
        self.logger = logger or setup_logger("person_detector")
        self.model = None
        self.person_class_id = None
        self.device = None

        self._load_model()

    # ------------------------------------------------------------------
    # Model loading & validation
    # ------------------------------------------------------------------
    def _load_model(self) -> None:
        """Load the YOLOv8 model and validate person class."""
        model_path = self.config.person_model_path

        # Validate model file exists
        if not model_path.exists():
            raise FileNotFoundError(
                f"Person detection model not found at: {model_path}\n"
                f"Please verify PERSON_MODEL_PATH in your .env file.\n"
                f"A COCO-pretrained model (e.g., yolov8n.pt) includes the 'person' class."
            )

        self.logger.info(f"Loading person detection model: {model_path}")

        try:
            self.model = YOLO(str(model_path))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load YOLOv8 model from {model_path}: {exc}\n"
                f"Ensure the file is a valid YOLOv8 .pt model."
            ) from exc

        self.logger.info("Model loaded successfully.")

        # Validate person class
        self._validate_person_class()

        # Resolve device
        from ai.utils import get_device

        self.device = get_device(self.config.device)
        self.logger.info(f"Device: {self.device.upper()}")

    def _validate_person_class(self) -> None:
        """
        Inspect the model's class names and verify "person" is present.

        Raises
        ------
        ValueError
            If the model does not contain a "person" class, with a
            clear explanation and remediation steps.
        """
        class_names = self.model.names  # dict: {id: name, ...}

        if not class_names:
            raise ValueError(
                f"Model at {self.config.person_model_path} has no class names.\n"
                f"This model cannot be used for person detection.\n"
                f"Set PERSON_MODEL_PATH to a COCO-pretrained YOLOv8 model."
            )

        # Search for "person" class (case-insensitive)
        for class_id, class_name in class_names.items():
            if class_name.lower() == "person":
                self.person_class_id = class_id
                self.logger.info(
                    f"Person class found — class_id={class_id} "
                    f"(model has {len(class_names)} classes total)"
                )
                return

        # Person class not found — provide detailed error
        available_classes = ", ".join(
            f"{cid}:{cname}" for cid, cname in sorted(class_names.items())
        )
        raise ValueError(
            f"═══════════════════════════════════════════════════════════\n"
            f"  MODEL DOES NOT CONTAIN 'person' CLASS\n"
            f"═══════════════════════════════════════════════════════════\n"
            f"\n"
            f"  Model path : {self.config.person_model_path}\n"
            f"  Classes    : {len(class_names)}\n"
            f"  Available  : {available_classes}\n"
            f"\n"
            f"  This model appears to be trained on a product-detection\n"
            f"  dataset (e.g., SKU-110K) and does NOT include a 'person'\n"
            f"  class required for person detection.\n"
            f"\n"
            f"  SOLUTION:\n"
            f"  Set PERSON_MODEL_PATH in your .env to a COCO-pretrained\n"
            f"  YOLOv8 model that includes the 'person' class.\n"
            f"\n"
            f"  Example:\n"
            f"    PERSON_MODEL_PATH=ai/yolov8n.pt\n"
            f"\n"
            f"  The standard yolov8n.pt model trained on COCO includes\n"
            f"  80 classes, with 'person' as class 0.\n"
            f"═══════════════════════════════════════════════════════════"
        )

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> tuple:
        """
        Run person detection on a single frame.

        Parameters
        ----------
        frame : np.ndarray
            BGR image frame from OpenCV.

        Returns
        -------
        tuple[List[Detection], float]
            List of person detections and inference time in milliseconds.
        """
        start = time.perf_counter()

        results = self.model.predict(
            source=frame,
            conf=self.config.confidence_threshold,
            imgsz=self.config.image_size,
            device=self.device,
            classes=[self.person_class_id],
            verbose=False,
        )

        inference_time_ms = (time.perf_counter() - start) * 1000

        detections: List[Detection] = []

        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = self.model.names.get(cls_id, "unknown")

                    detections.append(
                        Detection(
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            confidence=conf,
                            class_id=cls_id,
                            class_name=cls_name,
                        )
                    )

        return detections, inference_time_ms

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------
    def annotate(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Draw bounding boxes and labels on the frame.

        Parameters
        ----------
        frame : np.ndarray
            Original BGR frame.
        detections : List[Detection]
            Person detections to draw.

        Returns
        -------
        np.ndarray
            Annotated copy of the frame.
        """
        annotated = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), _BOX_COLOR, _BOX_THICKNESS)

            # Label text: "Person 0.87"
            label = f"Person {det.confidence:.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(
                label, _FONT, _FONT_SCALE, _FONT_THICKNESS
            )

            # Draw text background
            cv2.rectangle(
                annotated,
                (x1, y1 - text_h - baseline - 4),
                (x1 + text_w, y1),
                _TEXT_BG_COLOR,
                -1,
            )

            # Draw text
            cv2.putText(
                annotated,
                label,
                (x1, y1 - baseline - 2),
                _FONT,
                _FONT_SCALE,
                _TEXT_COLOR,
                _FONT_THICKNESS,
            )

        return annotated

    @property
    def model_path(self) -> Path:
        """Return the path of the loaded model."""
        return self.config.person_model_path

    @property
    def class_names(self) -> dict:
        """Return the model's class names dictionary."""
        return self.model.names if self.model else {}
