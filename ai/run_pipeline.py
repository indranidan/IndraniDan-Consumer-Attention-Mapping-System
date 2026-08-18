#!/usr/bin/env python3
"""
Consumer Attention Mapping System — Module 3 End-to-End Pipeline Runner
==========================================================================
Executes all Module 3 phases sequentially from a single video source:

  Phase 1: Person Detection       (ai/person_detection.py)
  Phase 2: Person Tracking        (ai/person_tracking.py)
  Phase 3: Movement Intelligence  (ai/movement_tracking.py)
  Phase 4: Dwell-Time Analytics   (ai/dwell_time.py)
  Phase 5: Attention / Gaze       (ai/attention_analysis.py)
  Phase 6: Attention Reporting    (ai/generate_attention_report.py)

Each phase runs sequentially upon completion of the preceding phase.
Outputs automatically overwrite existing files in designated phase folders under outputs/module3/.

Usage:
    python ai/run_pipeline.py --source /path/to/video.mp4
    python ai/run_pipeline.py --source 0
    python ai/run_pipeline.py --source video.mp4 --confidence 0.40 --device cpu
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Reconfigure standard streams to UTF-8 for cross-platform stability
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name == "ai" else _SCRIPT_DIR
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Consumer Attention Mapping System — Module 3 Master Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai/run_pipeline.py --source data/video.mp4
  python ai/run_pipeline.py --source 0
  python ai/run_pipeline.py --source video.mp4 --confidence 0.40 --device cpu
  python ai/run_pipeline.py --source video.mp4 --start-phase 3
        """,
    )
    parser.add_argument(
        "--source", "-s",
        required=True,
        help="Path to input video file or webcam index (e.g., '0')",
    )
    parser.add_argument(
        "--confidence", "--conf",
        type=float,
        default=None,
        help="Override PERSON_CONFIDENCE_THRESHOLD (0.0 - 1.0)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Override DEVICE preference: 'cpu', 'cuda', or 'auto'",
    )
    parser.add_argument(
        "--zones",
        type=str,
        default=None,
        help="Path to zones.json configuration file",
    )
    parser.add_argument(
        "--attention-regions",
        type=str,
        default=None,
        help="Path to attention_regions.json configuration file",
    )
    parser.add_argument(
        "--start-phase",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5, 6],
        help="Phase to start execution from (default: 1)",
    )
    return parser.parse_args()


def print_header(text: str) -> None:
    """Print formatted section header."""
    width = 70
    border = "=" * width
    print(f"\n{border}")
    print(f"  {text}")
    print(f"{border}\n")


def run_phase(phase_num: int, phase_name: str, command: list) -> bool:
    """Execute a single phase command synchronously and return True if successful."""
    start_time = time.perf_counter()
    print_header(f"MODULE 3 — PHASE {phase_num}: {phase_name.upper()}")

    cmd_str = " ".join(command)
    print(f"  Executing: {cmd_str}\n")

    try:
        # Pass environment with UTF-8 encoding enabled
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        # Run process synchronously, streaming output live to console
        res = subprocess.run(command, cwd=str(_PROJECT_ROOT), env=env, check=False)
        elapsed = time.perf_counter() - start_time

        if res.returncode == 0:
            print(f"\n  [OK] Phase {phase_num} ({phase_name}) completed successfully in {elapsed:.2f}s.\n")
            return True
        else:
            print(f"\n  [FAIL] Phase {phase_num} ({phase_name}) failed with exit code {res.returncode}.\n")
            return False

    except Exception as exc:
        print(f"\n  [ERROR] Failed to launch Phase {phase_num}: {exc}\n")
        return False


def main() -> None:
    """Master pipeline runner entry point."""
    args = parse_args()
    total_start = time.perf_counter()

    python_exe = sys.executable

    print_header("CONSUMER ATTENTION MAPPING SYSTEM — MODULE 3 FULL PIPELINE")
    print(f"  Source Input     : {args.source}")
    print(f"  Starting Phase   : {args.start_phase}")
    print(f"  Python Executable: {python_exe}")
    print(f"  Project Root     : {_PROJECT_ROOT}")

    # Build commands for each phase
    phases = []

    # Phase 1: Person Detection
    p1_cmd = [python_exe, "ai/person_detection.py", "--source", args.source]
    if args.confidence is not None:
        p1_cmd.extend(["--confidence", str(args.confidence)])
    phases.append((1, "Person Detection", p1_cmd))

    # Phase 2: Multi-Person Tracking (ByteTrack)
    p2_cmd = [python_exe, "ai/person_tracking.py", "--source", args.source]
    if args.confidence is not None:
        p2_cmd.extend(["--confidence", str(args.confidence)])
    phases.append((2, "Person Tracking (ByteTrack)", p2_cmd))

    # Phase 3: Movement Analysis
    p3_cmd = [python_exe, "ai/movement_tracking.py", "--source", args.source]
    if args.confidence is not None:
        p3_cmd.extend(["--confidence", str(args.confidence)])
    if args.zones:
        p3_cmd.extend(["--zones", args.zones])
    phases.append((3, "Movement Analysis", p3_cmd))

    # Phase 4: Dwell-Time Analytics
    p4_cmd = [python_exe, "ai/dwell_time.py", "--source", args.source]
    if args.confidence is not None:
        p4_cmd.extend(["--conf", str(args.confidence)])
    if args.device:
        p4_cmd.extend(["--device", args.device])
    if args.zones:
        p4_cmd.extend(["--zones", args.zones])
    phases.append((4, "Dwell-Time Analytics", p4_cmd))

    # Phase 5: Attention / Gaze Analysis
    p5_cmd = [python_exe, "ai/attention_analysis.py", "--source", args.source]
    if args.confidence is not None:
        p5_cmd.extend(["--conf", str(args.confidence)])
    if args.device:
        p5_cmd.extend(["--device", args.device])
    if args.zones:
        p5_cmd.extend(["--zones", args.zones])
    if args.attention_regions:
        p5_cmd.extend(["--attention-regions", args.attention_regions])
    phases.append((5, "Attention & Gaze Analysis", p5_cmd))

    # Phase 6: Attention Reports
    p6_cmd = [python_exe, "ai/generate_attention_report.py"]
    phases.append((6, "Attention Reports & Analytics", p6_cmd))

    # Execute selected phases
    completed_phases = []
    failed_phase = None

    for num, name, cmd in phases:
        if num < args.start_phase:
            print(f"  [Skipping Phase {num}: {name} (start-phase is {args.start_phase})]")
            continue

        success = run_phase(num, name, cmd)
        if success:
            completed_phases.append((num, name))
        else:
            failed_phase = (num, name)
            break

    # Summary
    total_elapsed = time.perf_counter() - total_start
    print_header("MODULE 3 PIPELINE EXECUTION SUMMARY")

    print(f"  Total Execution Time: {total_elapsed:.2f} seconds\n")
    print("  Phase Status:")
    for num, name in completed_phases:
        print(f"    [COMPLETED] Phase {num}: {name}")

    if failed_phase:
        num, name = failed_phase
        print(f"    [FAILED] Phase {num}: {name}")
        print(f"\n  [FAIL] Pipeline terminated due to error in Phase {num}")
        sys.exit(1)
    else:
        print("\n  [SUCCESS] All Module 3 phases executed successfully!")
        print("\n  Generated Reports Location:")
        print("    - Phase 1: outputs/module3/phase1/reports/")
        print("    - Phase 2: outputs/module3/phase2/reports/")
        print("    - Phase 3: outputs/module3/phase3/reports/")
        print("    - Phase 4: outputs/module3/phase4/reports/")
        print("    - Phase 5: outputs/module3/phase5/reports/")
        print("    - Phase 6: outputs/module3/phase6/reports/")
        print("\n  Generated Charts Location:")
        print("    - Phase 4: outputs/module3/phase4/plots/")
        print("    - Phase 5: outputs/module3/phase5/plots/")
        print("    - Phase 6: outputs/module3/phase6/plots/")
        print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
