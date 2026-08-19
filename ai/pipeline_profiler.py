"""
Pipeline Profiler
=================
Lightweight performance profiling helper for tracking per-phase and per-frame
execution time in the unified Module 3 AI pipeline.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Optional
from ai.logger import setup_logger

class PipelineProfiler:
    """Tracks timing metrics for video processing phases."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or setup_logger("pipeline_profiler")
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.total_frames: int = 0
        
        # Accumulators for times in milliseconds
        self.phase_times_ms: Dict[str, float] = defaultdict(float)
        self.phase_counts: Dict[str, int] = defaultdict(int)

    def start_pipeline(self) -> None:
        """Mark start of entire pipeline."""
        self.start_time = time.perf_counter()

    def stop_pipeline(self) -> float:
        """Mark end of entire pipeline and return total duration in seconds."""
        self.end_time = time.perf_counter()
        return self.total_duration_sec

    @property
    def total_duration_sec(self) -> float:
        if self.start_time > 0 and self.end_time > 0:
            return self.end_time - self.start_time
        elif self.start_time > 0:
            return time.perf_counter() - self.start_time
        return 0.0

    def record_phase(self, phase_name: str, duration_ms: float) -> None:
        """Record elapsed time for a phase step in milliseconds."""
        self.phase_times_ms[phase_name] += duration_ms
        self.phase_counts[phase_name] += 1

    def print_summary(self, video_fps: float = 0.0) -> None:
        """Log a formatted summary table of performance metrics."""
        total_sec = self.total_duration_sec
        eff_fps = (self.total_frames / total_sec) if total_sec > 0 else 0.0

        self.logger.info("======================================================================")
        self.logger.info("  UNIFIED PIPELINE PERFORMANCE PROFILING SUMMARY")
        self.logger.info("======================================================================")
        self.logger.info(f"  Total Frames Processed : {self.total_frames:,}")
        self.logger.info(f"  Total Pipeline Time    : {total_sec:.2f} s")
        self.logger.info(f"  Effective Processing   : {eff_fps:.2f} FPS")
        if video_fps > 0:
            speedup = eff_fps / video_fps
            self.logger.info(f"  Speed vs Realtime      : {speedup:.2f}x realtime")
        self.logger.info("  ──────────────────────────────────────────────────────────────────")
        self.logger.info("  Phase Timing Breakdown:")
        
        for phase, total_ms in self.phase_times_ms.items():
            count = self.phase_counts[phase]
            avg_ms = total_ms / count if count > 0 else 0.0
            pct = (total_ms / 1000.0 / total_sec * 100.0) if total_sec > 0 else 0.0
            self.logger.info(f"    • {phase:<25}: Total {total_ms/1000.0:6.2f}s | Avg {avg_ms:6.2f}ms/frame | {pct:5.1f}%")
        self.logger.info("======================================================================")
