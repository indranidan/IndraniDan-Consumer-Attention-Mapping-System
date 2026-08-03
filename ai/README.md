# 🤖 AI Module — SKU-110K YOLOv8 Transfer Learning Pipeline

**Phase 2: Production-Ready Training Pipeline for Retail Shelf Product Detection**

This module provides the complete, production-ready YOLOv8 transfer learning pipeline for the **SKU-110K** dataset within the Consumer Attention Mapping System. It is an independent AI layer that operates alongside `backend/` and `frontend/` without modifying any existing backend or frontend source code.

---

## 📁 Folder Structure

```
ai/
├── config.py             # Centralized environment & training configuration loader (.env)
├── train.py              # ★ YOLOv8 transfer learning pipeline (Phase 2)
├── training_utils.py     # ★ Training utilities: plots, reports, checkpoints (Phase 2)
├── dataset.py            # COCO & SKU-110K dataset validation, pairing & statistics
├── verify_dataset.py     # CLI: Validate COCO 2017 & SKU-110K datasets
├── verify_sku110k.py     # CLI: Comprehensive SKU-110K dataset validator & image-label matcher
├── generate_yaml.py      # CLI: Dynamic data.yaml generator for YOLOv8
├── download_model.py     # CLI: Pretrained yolov8n.pt verifier & automatic downloader
├── train_config.py       # CLI: Training environment inspector & directory creator
├── logger.py             # Structured logging framework
├── utils.py              # Directory management, timer, banner & device helpers
├── requirements.txt      # Python dependencies
├── README.md             # Architecture, setup & execution documentation
├── yolov8n.pt            # Base pretrained YOLOv8 nano model
├── configs/              # Automatically generated YAML dataset configurations
│   └── sku110k.yaml      # Dynamic dataset config for YOLOv8
├── models/               # Pretrained weights store
└── outputs/              # Structured output root
    ├── training/         # Training runs & checkpoints
    │   ├── weights/      #   best.pt & last.pt
    │   ├── metrics/      #   results.csv (per-epoch metrics)
    │   ├── plots/        #   Loss, Precision, Recall, mAP curves
    │   ├── logs/         #   training.log
    │   └── reports/      #   training_report.md
    ├── evaluation/       # Evaluation metrics, confusion matrix & reports
    ├── weights/          # Legacy model weights storage
    ├── plots/            # Legacy training visual plots
    ├── logs/             # Pipeline execution log files
    └── reports/          # Verification & diagnostic reports
```

---

## 📋 Prerequisites & Hardware Specifications

| Requirement | Specification / Recommended |
|-------------|----------------------------|
| Operating System | Kali Linux / Linux |
| Processor (CPU) | AMD Ryzen 3 3250U (2 cores, 4 threads) |
| System RAM | 8 GB |
| Python Version | Python 3.10+ |
| Compute Device | CPU (automatic GPU detection if CUDA is available) |
| SKU-110K Dataset | Stored at `/home/cyborg/Storage/datasets/SKU 110k/SKU110K_fixed` |

---

## ⚙️ Environment Variables Setup

All paths and hyperparameter settings are dynamically loaded from `.env` in the project root. **No hardcoded paths exist in the code.**

Copy `.env.example` to `.env` if not already present:

```bash
cp .env.example .env
```

Ensure `.env` contains the following AI parameters:

```env
# ── AI Module Settings ─────────────────────────────────────────
COCO_DATASET_PATH=/home/cyborg/Storage/datasets/COCO 2017
SKU110K_DATASET_PATH=/home/cyborg/Storage/datasets/SKU 110k/SKU110K_fixed
YOLO_MODEL_NAME=yolov8n.pt
YOLO_OUTPUT_PATH=ai/outputs
DEVICE=cpu
IMAGE_SIZE=640
BATCH_SIZE=4
EPOCHS=50
WORKERS=2
PROJECT_NAME=sku110k_training
RUN_NAME=yolov8n_sku110k_run1
OUTPUT_DIRECTORY=ai/outputs
RESUME_TRAINING=false
SEED=42
MAX_EVAL_SAMPLES=100
CONFIDENCE_THRESHOLD=0.25
```

### Training Parameter Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `YOLO_MODEL_NAME` | `yolov8n.pt` | Base pretrained model for transfer learning |
| `IMAGE_SIZE` | `640` | Input image resolution (pixels) |
| `BATCH_SIZE` | `4` | Images per training batch (reduce if OOM) |
| `EPOCHS` | `50` | Total training epochs |
| `DEVICE` | `cpu` | Compute device (`cpu`, `cuda`, `cuda:0`, `auto`) |
| `WORKERS` | `2` | DataLoader worker processes |
| `PROJECT_NAME` | `sku110k_training` | Training project identifier |
| `RUN_NAME` | `yolov8n_sku110k_run1` | Unique run name within project |
| `OUTPUT_DIRECTORY` | `ai/outputs` | Base directory for all outputs |
| `RESUME_TRAINING` | `false` | Set `true` to resume from last.pt |
| `SEED` | `42` | Random seed for reproducibility |
| `CONFIDENCE_THRESHOLD` | `0.25` | Minimum confidence for detections |

---

## 🚀 Setup Instructions

1. Activate your virtual environment:

```bash
source venv/bin/activate
```

2. Install or update required dependencies:

```bash
pip install -r ai/requirements.txt
```

---

## ▶️ Execution Instructions

Every CLI module in `ai/` runs independently from the project root without needing backend or frontend services.

### 🏋️ Train YOLOv8 on SKU-110K (Phase 2)

Fine-tune the pretrained YOLOv8 model on the SKU-110K dataset using transfer learning:

```bash
python ai/train.py
```

**What happens:**

1. Loads all configuration from `.env`
2. Automatically detects CPU or GPU
3. Validates `ai/configs/sku110k.yaml` and dataset directories
4. Locates the pretrained `yolov8n.pt` model
5. Creates structured output directories
6. Starts YOLOv8 transfer learning with progress display
7. Saves `best.pt` and `last.pt` checkpoints
8. Generates training curves (Loss, Precision, Recall, mAP)
9. Generates a Markdown training report

**Output:**

```
outputs/training/
├── weights/
│   ├── best.pt              # Best mAP checkpoint
│   └── last.pt              # Latest epoch checkpoint
├── metrics/
│   └── results.csv          # Per-epoch training metrics
├── plots/
│   ├── loss_curve.png       # Box, CLS, DFL loss curves
│   ├── precision_curve.png  # Precision over epochs
│   ├── recall_curve.png     # Recall over epochs
│   ├── map_curve.png        # mAP50 & mAP50-95 curves
│   └── training_summary.png # Combined 2×2 overview
├── logs/
│   └── training.log         # Full training log
└── reports/
    └── training_report.md   # Training summary report
```

#### Resuming Interrupted Training

If training is interrupted (Ctrl+C, crash, power loss), resume from the last checkpoint:

1. Set in `.env`:
   ```env
   RESUME_TRAINING=true
   ```
2. Run again:
   ```bash
   python ai/train.py
   ```

The pipeline will automatically load `last.pt` and continue training.

#### Quick Test Run

To verify the pipeline works before a full training run, temporarily set in `.env`:

```env
EPOCHS=1
BATCH_SIZE=2
```

Then run `python ai/train.py`. After verification, restore your original values.

---

### 1. Verify SKU-110K Dataset

Validates that `images/` and `labels/` exist with `train`, `val`, `test` subdirectories, counts all files, and verifies image-to-label pairing.

```bash
python ai/verify_sku110k.py
```

**Output Includes:**
- Verification of root path, `images/`, and `labels/` subdirectories
- Match verification (confirming every image has a `.txt` label file)
- Complete statistics table listing image, label, and matched counts for `train`, `val`, and `test` splits

---

### 2. Generate Dynamic `data.yaml`

Generates `ai/configs/sku110k.yaml` dynamically using paths from `.env`. Validates YAML structure before and after saving.

```bash
python ai/generate_yaml.py
```

**Output File:** `ai/configs/sku110k.yaml`

```yaml
# YOLOv8 Dataset Configuration for SKU-110K
path: /home/cyborg/Storage/datasets/SKU 110k/SKU110K_fixed
train: images/train
val: images/val
test: images/test
nc: 1
names:
  0: object
```

---

### 3. Verify / Download Pretrained YOLO Model

Verifies presence of `yolov8n.pt`. Downloads it automatically if missing and inspects PyTorch, Ultralytics, and compute device environment.

```bash
python ai/download_model.py
```

**Output Includes:**
- PyTorch and Ultralytics version check
- CUDA availability & CPU device fallback check
- Model filename, path, and file size in MB

---

### 4. Inspect Training Configuration

Loads and prints all training parameters from `.env` and initializes required `outputs/` subdirectories.

```bash
python ai/train_config.py
```

**Output Includes:**
- Parameter listing for `MODEL_NAME`, `IMAGE_SIZE`, `BATCH_SIZE`, `EPOCHS`, `DEVICE`, `WORKERS`, `PROJECT_NAME`, `RUN_NAME`, `OUTPUT_DIRECTORY`, `RESUME_TRAINING`, `SEED`
- Creation of `outputs/{training,evaluation,logs,weights,plots,reports}`

---

## 📄 Explanation of Every Generated File

### `train.py` ★ New in Phase 2
Production-ready YOLOv8 transfer learning pipeline. Orchestrates the entire training workflow as a class-based pipeline (`TrainingPipeline`):
- Loads all configuration from `.env` via `config.py`
- Auto-detects CUDA or falls back to CPU via `utils.get_device()`
- Validates dataset YAML and pretrained model locations
- Runs Ultralytics `model.train()` with transfer learning
- Handles OOM, CUDA errors, and keyboard interrupts gracefully
- Copies checkpoints (`best.pt`, `last.pt`) to canonical output directory
- Triggers post-training plot generation and report creation

### `training_utils.py` ★ New in Phase 2
Reusable utility functions extracted from the training pipeline (SRP/SOLID):
- `validate_dataset_yaml()`: Loads and validates YOLO dataset YAML configuration
- `locate_pretrained_model()`: Searches standard locations for the `.pt` model file
- `setup_training_directories()`: Creates `outputs/training/{weights,metrics,plots,logs,reports}`
- `copy_checkpoints()`: Copies `best.pt` and `last.pt` to canonical weights directory
- `copy_metrics()`: Copies `results.csv` to metrics directory
- `generate_training_plots()`: Creates matplotlib visualizations (loss, precision, recall, mAP curves)
- `generate_training_report()`: Generates `training_report.md` with full run metadata and final metrics
- `format_duration()`: Converts seconds to `HH:MM:SS` format

### `logger.py`
Standard logging framework for the AI module. Formats stdout logs with timestamp, log level, and logger name. Supports writing log streams to disk under `ai/outputs/logs/`.

### `config.py`
Centralized environment loader using `python-dotenv`. Reads `.env` and constructs an immutable `AIConfig` dataclass containing typed attributes for dataset paths, YOLO model options, compute device settings, and training hyperparameters.

### `utils.py`
Helper utilities shared across the module:
- `get_device()`: Detects CUDA availability or applies CPU fallback.
- `ensure_directory()`: Recursively creates missing directories.
- `setup_output_directories()`: Initializes `outputs/{training,evaluation,logs,weights,plots,reports}`.
- `timer()`: Context manager for measuring execution time.
- `print_banner()`: Formats section titles in stdout.

### `dataset.py`
Dataset inspection engine containing:
- `verify_and_count_sku110k()`: Scans `SKU110K_DATASET_PATH` for `images/{train,val,test}` and `labels/{train,val,test}`, verifies file pairing, detects empty/corrupted labels, and gathers statistical metadata.
- `validate_coco_dataset()`: Validates COCO 2017 structure.

### `verify_sku110k.py`
CLI script. Calls `verify_and_count_sku110k()` and renders a statistical report table for training, validation, and testing splits. Exits with code 0 on success.

### `generate_yaml.py`
CLI script. Reads `SKU110K_DATASET_PATH` from `.env`, creates `ai/configs/sku110k.yaml`, and verifies valid YAML schema.

### `download_model.py`
CLI script. Ensures `yolov8n.pt` exists in `ai/models/` (downloading via Ultralytics if missing), checks PyTorch/Ultralytics versions, CUDA status, and displays model size.

### `train_config.py`
CLI script. Inspects training hyperparameters, ensures 0 hardcoded settings, creates output directory trees, and confirms infrastructure readiness.

### `requirements.txt`
Pinned Python dependencies including `ultralytics`, `torch`, `torchvision`, `opencv-python`, `python-dotenv`, `PyYAML`, `pycocotools`, `matplotlib`, `numpy`, and `Pillow`.

---

## 🛡️ Error Handling

The pipeline handles:
- **Invalid Dataset**: Clear alert when `SKU110K_DATASET_PATH` is invalid or absent.
- **Missing Images/Labels**: Detects missing split directories (`train`, `val`, `test`).
- **Missing Labels**: Identifies images without corresponding `.txt` label files.
- **Missing YAML**: Prompts user to run `generate_yaml.py` if `sku110k.yaml` is missing.
- **Invalid Model**: Graceful error if pretrained `.pt` file is corrupted or absent.
- **CUDA Unavailable**: Automatic fallback to CPU with informative warning.
- **Out of Memory**: Catches CUDA OOM and general OOM, suggests reducing batch/image size.
- **Missing `.env`**: Validates required environment variables with clear fix suggestions.
- **Permission Errors**: Gracefully logs read/write permission issues.
- **Interrupted Training**: Catches `KeyboardInterrupt`, saves progress, suggests resume.

---

## 🏁 Summary

With this module:
1. `verify_sku110k.py` confirms dataset integrity.
2. `generate_yaml.py` outputs the exact YAML configuration required for Ultralytics YOLOv8.
3. `download_model.py` ensures pretrained weights are available.
4. `train_config.py` verifies training configuration and output directories.
5. **`train.py` fine-tunes YOLOv8 on SKU-110K via transfer learning and produces `best.pt`, `last.pt`, training plots, and a training report.**

**The system is production-ready for YOLOv8 transfer learning on SKU-110K.**
