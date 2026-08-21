"""
AI Worker
==========
Background worker that executes the existing Module 3 AI pipeline
via subprocess. Runs in a separate thread to avoid blocking FastAPI.

The worker calls ai/run_pipeline.py exactly as designed — no modifications
to the AI pipeline code.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.ai_job import AIJob

# ── Module-level state ────────────────────────────────────────
_logger = logging.getLogger("ai_worker")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter("[%(asctime)s] [WORKER] [%(levelname)-8s] %(message)s", "%Y-%m-%d %H:%M:%S")
)
if not _logger.handlers:
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)

# Track running processes for stop functionality
_running_processes: dict[str, subprocess.Popen] = {}
_stopped_jobs: set[str] = set()
_lock = threading.Lock()


def _get_project_root() -> Path:
    """Determine the project root directory."""
    # backend/ is a child of the project root
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent
    return project_root


def _update_job_status(
    job_id: uuid.UUID,
    status: str,
    error_message: Optional[str] = None,
    summary: Optional[dict] = None,
    output_path: Optional[str] = None,
    started: bool = False,
    completed: bool = False,
) -> None:
    """Update job status in a new database session (thread-safe)."""
    db: Session = SessionLocal()
    try:
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if not job:
            _logger.error(f"Job {job_id} not found in database")
            return

        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if summary is not None:
            job.summary = summary
        if output_path is not None:
            job.output_path = output_path
        if started:
            job.started_at = datetime.now(timezone.utc)
        if completed:
            job.completed_at = datetime.now(timezone.utc)

        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        _logger.info(f"Job {job_id} status updated to {status}")
    except Exception as exc:
        _logger.error(f"Failed to update job {job_id}: {exc}")
        db.rollback()
    finally:
        db.close()


def _read_phase6_report(output_dir: Path) -> Optional[dict]:
    """
    Read the Phase 6 JSON report to extract summary analytics.
    Returns the report dict or None if not found.
    """
    if not output_dir.is_absolute():
        output_dir = _get_project_root() / output_dir
    reports_dir = output_dir / "phase6" / "reports"
    if not reports_dir.exists():
        _logger.warning(f"Phase 6 reports directory not found: {reports_dir}")
        return None

    # Find the JSON report file
    json_files = list(reports_dir.glob("*.json"))
    if not json_files:
        _logger.warning(f"No JSON reports found in {reports_dir}")
        return None

    report_file = json_files[0]  # Take the first/only report
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            report = json.load(f)
        _logger.info(f"Loaded Phase 6 report: {report_file}")
        return report
    except Exception as exc:
        _logger.error(f"Failed to read Phase 6 report {report_file}: {exc}")
        return None


def _extract_summary(report: dict) -> dict:
    """Extract compact summary from the full Phase 6 report."""
    summary_section = report.get("summary", {})

    return {
        "unique_shoppers": summary_section.get("total_unique_shoppers", 0),
        "total_sessions": summary_section.get("total_sessions", 0),
        "completed_sessions": summary_section.get("completed_sessions", 0),
        "total_entries": summary_section.get("total_entries", 0),
        "total_exits": summary_section.get("total_exits", 0),
        "average_session_duration_sec": summary_section.get("average_session_duration_sec", 0),
        "total_zone_visits": summary_section.get("total_zone_visits", 0),
        "average_zone_dwell_time_sec": summary_section.get("average_zone_dwell_time_sec", 0),
        "total_attention_events": summary_section.get("total_attention_events", 0),
        "total_estimated_attention_duration_sec": summary_section.get(
            "total_estimated_attention_duration_sec", 0
        ),
        "average_estimated_attention_duration_sec": summary_section.get(
            "average_estimated_attention_duration_sec", 0
        ),
        "number_of_attention_targets": summary_section.get("number_of_attention_targets", 0),
        "most_visited_zone": summary_section.get("most_visited_zone"),
        "most_attended_target": summary_section.get("most_attended_target"),
    }


def _collect_available_files(output_dir: Path) -> list[str]:
    """Collect list of available output files (relative paths)."""
    files = []
    if not output_dir.exists():
        return files

    for phase_dir in sorted(output_dir.iterdir()):
        if phase_dir.is_dir():
            for sub_dir in sorted(phase_dir.iterdir()):
                if sub_dir.is_dir():
                    for f in sorted(sub_dir.iterdir()):
                        if f.is_file() and not f.name.startswith("."):
                            rel = f.relative_to(output_dir)
                            files.append(str(rel))
    return files


def run_pipeline(
    job_id: uuid.UUID,
    source: str,
    output_base_path: str,
    pipeline_timeout: int = 3600,
) -> None:
    """
    Execute the AI pipeline in a background thread.

    This function:
    1. Updates job status to RUNNING
    2. Sets environment variables to redirect pipeline outputs
    3. Calls ai/run_pipeline.py via subprocess
    4. On completion, reads results and updates job with summary
    5. On failure, captures error and updates job status

    Parameters
    ----------
    job_id : uuid.UUID
        The AI job ID.
    source : str
        Video source path or camera URL.
    output_base_path : str
        Base path for this job's output files.
    pipeline_timeout : int
        Maximum seconds to allow the pipeline to run.
    """
    project_root = _get_project_root()
    job_output_dir = Path(output_base_path)

    _logger.info(f"Starting AI pipeline for job {job_id}")
    _logger.info(f"  Source: {source}")
    _logger.info(f"  Output: {job_output_dir}")
    _logger.info(f"  Project root: {project_root}")
    _logger.info(f"  Timeout: {pipeline_timeout}s")

    # Update status to RUNNING
    _update_job_status(job_id, "RUNNING", started=True)

    # Create output directory
    job_output_dir.mkdir(parents=True, exist_ok=True)

    # Build environment with redirected output paths & UTF-8 stdio
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # Redirect all phase outputs to job-specific directory
    env["AI_JOB_OUTPUT_PATH"] = str(job_output_dir)
    env["PHASE1_OUTPUT_PATH"] = str(job_output_dir / "phase1" / "reports")
    env["PHASE2_OUTPUT_PATH"] = str(job_output_dir / "phase2" / "reports")
    env["MOVEMENT_OUTPUT_PATH"] = str(job_output_dir / "phase3")
    env["PHASE3_OUTPUT_PATH"] = str(job_output_dir / "phase3" / "reports")
    env["PHASE4_OUTPUT_PATH"] = str(job_output_dir / "phase4" / "reports")
    env["PHASE5_OUTPUT_PATH"] = str(job_output_dir / "phase5" / "reports")
    env["PHASE6_OUTPUT_PATH"] = str(job_output_dir / "phase6")
    env["DWELL_OUTPUT_PATH"] = str(job_output_dir / "phase4")
    env["ATTENTION_OUTPUT_PATH"] = str(job_output_dir / "phase5")

    # Build the pipeline command
    python_exe = sys.executable
    pipeline_script = str(project_root / "ai" / "run_pipeline.py")

    cmd = [python_exe, pipeline_script, "--source", source]

    _logger.info(f"  Command: {' '.join(cmd)}")

    process = None
    job_id_str = str(job_id)
    try:
        # Start subprocess with UTF-8 encoding
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # Register running process for stop capability
        with _lock:
            _running_processes[job_id_str] = process

        # Stream output to log
        output_lines = []
        try:
            start_time = time.time()
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > pipeline_timeout:
                    _logger.error(f"Job {job_id} exceeded timeout of {pipeline_timeout}s")
                    process.kill()
                    _update_job_status(
                        job_id,
                        "FAILED",
                        error_message=f"Pipeline exceeded maximum timeout of {pipeline_timeout} seconds.",
                        completed=True,
                    )
                    return

                # Read output
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.rstrip()
                    output_lines.append(line)
                    _logger.info(f"  [AI] {line}")

        except Exception as read_exc:
            _logger.error(f"Error reading pipeline output: {read_exc}")

        # Wait for process to complete
        return_code = process.wait()

        # Unregister process & check if it was stopped
        with _lock:
            was_stopped = job_id_str in _stopped_jobs
            _stopped_jobs.discard(job_id_str)
            _running_processes.pop(job_id_str, None)

        sigterm = getattr(signal, "SIGTERM", None)
        sigkill = getattr(signal, "SIGKILL", None)
        signal_stopped = False
        if sigterm is not None and return_code in (sigterm, -sigterm):
            signal_stopped = True
        if sigkill is not None and return_code in (sigkill, -sigkill):
            signal_stopped = True

        if return_code == 0:
            _logger.info(f"Job {job_id} pipeline completed successfully")

            # Read Phase 6 report for summary
            report = _read_phase6_report(job_output_dir)
            summary = _extract_summary(report) if report else {
                "note": "Pipeline completed but Phase 6 report was not found. "
                        "Check phase outputs manually.",
            }

            # Compute relative output path for storage
            try:
                rel_output = str(job_output_dir.relative_to(project_root))
            except ValueError:
                rel_output = str(job_output_dir)

            _update_job_status(
                job_id,
                "COMPLETED",
                summary=summary,
                output_path=rel_output,
                completed=True,
            )

            # Automatically run Module 4 Attention Engine to persist aggregate analysis & reports
            try:
                from app.services.module4_service import get_or_run_module4_analysis
                m4_db: Session = SessionLocal()
                try:
                    get_or_run_module4_analysis(m4_db, job_id)
                    _logger.info(f"Module 4 Attention Analysis completed and persisted for job {job_id}")
                finally:
                    m4_db.close()
            except Exception as m4_exc:
                _logger.warning(f"Could not auto-generate Module 4 analysis for job {job_id}: {m4_exc}")

            # Automatically run Module 5 Product Interaction Analysis to persist aggregate analysis & reports
            try:
                from app.services.module5_service import get_or_run_module5_analysis
                m5_db: Session = SessionLocal()
                try:
                    get_or_run_module5_analysis(m5_db, job_id)
                    _logger.info(f"Module 5 Product Interaction Analysis completed and persisted for job {job_id}")
                finally:
                    m5_db.close()
            except Exception as m5_exc:
                _logger.warning(f"Could not auto-generate Module 5 analysis for job {job_id}: {m5_exc}")

        elif was_stopped or signal_stopped:
            _logger.info(f"Job {job_id} was stopped by user")
            _update_job_status(
                job_id,
                "STOPPED",
                error_message="Job was stopped by user request.",
                completed=True,
            )
        else:
            # Pipeline failed
            last_lines = output_lines[-20:] if output_lines else ["No output captured"]
            error_detail = "\n".join(last_lines)
            _logger.error(f"Job {job_id} pipeline failed with exit code {return_code}")

            _update_job_status(
                job_id,
                "FAILED",
                error_message=f"Pipeline exited with code {return_code}.\n\n"
                              f"Last output:\n{error_detail}",
                completed=True,
            )

    except FileNotFoundError:
        _logger.error(f"Pipeline script not found: {pipeline_script}")
        _update_job_status(
            job_id,
            "FAILED",
            error_message=f"Pipeline script not found at {pipeline_script}. "
                          f"Verify the AI module is properly installed.",
            completed=True,
        )
    except MemoryError:
        _logger.error(f"Job {job_id} ran out of memory")
        _update_job_status(
            job_id,
            "FAILED",
            error_message="Out of memory. Try using a shorter video or reduce IMAGE_SIZE.",
            completed=True,
        )
    except Exception as exc:
        _logger.error(f"Job {job_id} failed with unexpected error: {exc}")
        _update_job_status(
            job_id,
            "FAILED",
            error_message=f"Unexpected worker error: {str(exc)}",
            completed=True,
        )
    finally:
        # Ensure process is cleaned up
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception:
                pass

        # Ensure process is unregistered
        with _lock:
            _running_processes.pop(job_id_str, None)
            _stopped_jobs.discard(job_id_str)


def stop_job(job_id: uuid.UUID) -> bool:
    """
    Request to stop a running AI job.

    Returns True if a running process was found and terminated.
    """
    job_id_str = str(job_id)
    with _lock:
        _stopped_jobs.add(job_id_str)
        process = _running_processes.get(job_id_str)

    if process and process.poll() is None:
        _logger.info(f"Stopping job {job_id}...")
        try:
            process.terminate()
            # Give it a few seconds to shut down gracefully
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        except Exception as exc:
            _logger.error(f"Error stopping job {job_id}: {exc}")
            return False

        _update_job_status(
            job_id,
            "STOPPED",
            error_message="Job was stopped by user request.",
            completed=True,
        )
        return True

    return False


def get_running_job_count() -> int:
    """Return the number of currently running AI jobs."""
    with _lock:
        return sum(1 for p in _running_processes.values() if p.poll() is None)
