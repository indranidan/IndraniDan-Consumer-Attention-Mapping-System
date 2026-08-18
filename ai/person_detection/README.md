# Module 3 — Phase 1: Person Detection Pipeline

> **Independent CV pipeline for person detection using YOLOv8 + OpenCV**
>
> Part of the Indrani Consumer Attention Mapping System

---

## Overview

This module implements a standalone person detection pipeline that:

1. Reads video files or live webcam input via OpenCV
2. Runs YOLOv8 inference to detect persons
3. Draws annotated bounding boxes with confidence scores
4. Saves annotated output videos
5. Generates structured detection reports (JSON + Markdown)

```
Input (Video/Webcam)
        ↓
    OpenCV
        ↓
    YOLOv8
        ↓
  Person Detection
        ↓
  Bounding Boxes + Confidence
        ↓
  Annotated Video + Report
```

This pipeline is **completely independent** from the existing backend, frontend, and database.

---

## Architecture

```
ai/
├── person_detection.py              # CLI entry point
├── person_detection/
│   ├── __init__.py                  # Package marker
│   ├── config.py                    # PersonDetectionConfig (reads .env)
│   ├── detector.py                  # PersonDetector (model + inference + annotation)
│   ├── video_processor.py           # VideoProcessor (OpenCV input/output)
│   └── report.py                    # ReportGenerator (JSON + Markdown)
├── config.py                        # Shared AIConfig (NOT modified)
├── logger.py                        # Shared logging (reused)
├── utils.py                         # Shared utilities (reused)
└── tests/
    └── test_person_detection.py     # Test suite

outputs/
└── module3/
    └── phase1/
        ├── videos/                  # Annotated output videos
        ├── frames/                  # Saved annotated frames (optional)
        ├── reports/                 # JSON + Markdown reports
        └── logs/                    # Session log files
```

---

## Setup

### Prerequisites

All dependencies are already in `ai/requirements.txt`:

```
ultralytics>=8.0.0
torch>=2.0.0
opencv-python>=4.8.0
python-dotenv>=1.0.0
numpy>=1.24.0
```

### Install (if not already done)

```bash
pip install -r ai/requirements.txt
```

### Configuration

The following variables in `.env` control person detection:

| Variable | Default | Description |
|---|---|---|
| `PERSON_MODEL_PATH` | `ai/yolov8n.pt` | Path to YOLOv8 model with "person" class |
| `PERSON_CONFIDENCE_THRESHOLD` | `0.40` | Min confidence for person detections |
| `IMAGE_SIZE` | `640` | YOLO input image size |
| `DEVICE` | `auto` | `auto`, `cpu`, or `cuda` |
| `SAVE_FRAMES` | `false` | Save annotated frames to disk |

> **Important**: `PERSON_MODEL_PATH` must point to a model that includes the "person" class.
> The standard `yolov8n.pt` (COCO-pretrained, 80 classes) works out of the box.
> A SKU-110K trained model will **not** contain a person class and will be rejected with a clear error message.

---

## Usage

### Process a Video File

```bash
python ai/person_detection.py --source /path/to/video.mp4
```

This will:
- Open and validate the video
- Process every frame through YOLOv8 person detection
- Save an annotated video to `outputs/module3/phase1/videos/`
- Generate reports in `outputs/module3/phase1/reports/`

### Live Webcam Detection

```bash
python ai/person_detection.py --source 0
```

- `0` = default webcam
- Press **Q** to quit
- Displays annotated frames in a live window

### Optional CLI Arguments

```bash
# Override confidence threshold
python ai/person_detection.py --source /path/to/video.mp4 --confidence 0.50

# Save annotated frames (frames with person detections)
python ai/person_detection.py --source /path/to/video.mp4 --save-frames

# Custom output directory
python ai/person_detection.py --source /path/to/video.mp4 --output-dir custom_output/
```

---

## Output

### Annotated Video
- Location: `outputs/module3/phase1/videos/<filename>_person_detection.mp4`
- Green bounding boxes with `Person 0.87` labels
- HUD overlay showing frame number, persons detected, inference time, FPS

### Detection Reports

**JSON** — `outputs/module3/phase1/reports/person_detection_report.json`

```json
{
  "report_type": "person_detection",
  "module": "Module 3 — Phase 1",
  "video_filename": "sample.mp4",
  "video_duration_sec": 30.0,
  "video_resolution": "1280x720",
  "total_frames_processed": 900,
  "total_person_detections": 1250,
  "average_inference_time_ms": 45.3,
  "average_confidence": 0.7823,
  "device": "cpu",
  ...
}
```

**Markdown** — `outputs/module3/phase1/reports/person_detection_report.md`

Human-readable report with tables for video info, detection results, performance metrics, and configuration.

---

## Model Validation

The pipeline validates that the configured model contains a "person" class:

- ✅ `yolov8n.pt` (COCO, 80 classes including "person") — **works**
- ❌ SKU-110K trained model (1 class: "object") — **rejected with clear error**

If the model lacks a "person" class, you'll see:

```
═══════════════════════════════════════════════════════════
  MODEL DOES NOT CONTAIN 'person' CLASS
═══════════════════════════════════════════════════════════

  This model appears to be trained on a product-detection
  dataset (e.g., SKU-110K) and does NOT include a 'person'
  class required for person detection.

  SOLUTION:
  Set PERSON_MODEL_PATH in your .env to a COCO-pretrained
  YOLOv8 model that includes the 'person' class.
═══════════════════════════════════════════════════════════
```

---

## Testing

```bash
# Run all tests
python -m pytest ai/tests/test_person_detection.py -v

# Run specific test class
python -m pytest ai/tests/test_person_detection.py::TestModelLoading -v
```

### Test Coverage

| Test | Validates |
|---|---|
| `test_config_loading` | Config reads from .env correctly |
| `test_config_immutable` | Config is frozen |
| `test_model_loading` | YOLOv8 loads from yolov8n.pt |
| `test_person_class_exists` | COCO model has "person" class |
| `test_person_class_missing_raises_error` | Missing model file raises error |
| `test_detector_initializes_with_coco_model` | Detector initializes end-to-end |
| `test_invalid_video_path` | Non-existent video path raises error |
| `test_webcam_failure_handling` | Invalid webcam index raises error |
| `test_cpu_fallback` | Device auto-detection works |
| `test_explicit_cpu` | Forced CPU selection works |
| `test_detection_output_structure` | Detection returns proper namedtuples |
| `test_annotation_returns_frame` | Annotation produces valid numpy array |
| `test_annotation_does_not_modify_original` | Original frame is untouched |
| `test_report_generation` | JSON + Markdown reports are created |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `Model not found` | Verify `PERSON_MODEL_PATH` in `.env` points to a valid `.pt` file |
| `Model does not contain 'person' class` | Use a COCO-pretrained model like `yolov8n.pt` |
| `Cannot open webcam` | Check webcam connection; try index 1 or 2 |
| `Cannot open video file` | Verify file path and format (MP4, AVI, MOV, MKV) |
| `Out of memory` | Reduce `IMAGE_SIZE` in `.env` (try 416 or 320) |
| Slow inference | Expected on CPU; use `DEVICE=cuda` if GPU is available |

---

## Scope & Limitations

This phase **only** answers: *"Where are the people in this frame?"*

**NOT implemented** (future phases):
- Object tracking (ByteTrack, DeepSORT)
- Person re-identification
- Gaze estimation / head pose
- Dwell time / attention analysis
- Heatmaps
- Database integration
- Frontend integration
- RTSP / network camera support
