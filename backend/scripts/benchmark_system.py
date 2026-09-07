"""
CAMS System Performance Benchmarking Utility
=============================================
Measures API response latency, request throughput, algorithm execution timing,
and database query efficiency across analytical endpoints (Modules 4, 6, 8, 9, 11, 12).

Usage:
    python scripts/benchmark_system.py [--iterations 50] [--output-json benchmark_results.json]
"""

import argparse
import json
import logging
import math
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure backend root and project root are on Python path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.database import SessionLocal, engine
from app.main import app
from app.modules.scoring.engine import Module8ScoringEngine
from app.modules.recommendation.engine import Module9RecommendationEngine
from app.modules.recommendation.simulator import PlanogramSimulator
from app.modules.recommendation.models import PlanogramSimulationRequest
from app.modules.reports.aggregators import RetailIntelligenceAggregator
from app.modules.reports.pdf_generator import ReportPDFGenerator
from app.modules.reports.excel_generator import ReportExcelGenerator
from app.modules.reports.csv_generator import ReportCSVGenerator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("benchmark")


# ── Statistical Calculation Helpers ──────────────────────────────────────

def compute_stats(timings_ms: List[float]) -> Dict[str, float]:
    """Compute min, max, mean, p50, p95, p99 from a series of durations in ms."""
    if not timings_ms:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_times = sorted(timings_ms)
    n = len(sorted_times)

    def percentile(p: float) -> float:
        idx = int(math.ceil((p / 100.0) * n)) - 1
        return sorted_times[max(0, min(idx, n - 1))]

    mean_val = sum(sorted_times) / n
    return {
        "min": round(sorted_times[0], 2),
        "max": round(sorted_times[-1], 2),
        "mean": round(mean_val, 2),
        "p50": round(percentile(50), 2),
        "p95": round(percentile(95), 2),
        "p99": round(percentile(99), 2),
    }


def measure_block(func: Callable, iterations: int = 20) -> tuple[Dict[str, float], float]:
    """Execute callable multiple times and measure latency stats and throughput."""
    timings = []
    # Warmup
    try:
        func()
    except Exception:
        pass

    start_total = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        func()
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000.0)
    total_wall_sec = time.perf_counter() - start_total
    qps = round(iterations / total_wall_sec, 1) if total_wall_sec > 0 else 0.0

    return compute_stats(timings), qps


# ── Benchmark Suite ──────────────────────────────────────────────────────

class CAMSBenchmarkSuite:
    """Orchestrates latency and throughput measurements across all CAMS layers."""

    def __init__(self, iterations: int = 30):
        self.iterations = iterations
        self.client = TestClient(app)
        self.results: Dict[str, Any] = {}

    def benchmark_database_query_pool(self) -> Dict[str, Any]:
        """Measure database connection acquisition and query timing."""
        logger.info("-> Benchmarking Database Query Pool...")

        def _db_probe():
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))

        stats, qps = measure_block(_db_probe, iterations=self.iterations)
        return {
            "name": "Database Ping (Connection Pool)",
            "stats_ms": stats,
            "throughput_qps": qps,
            "target_sla_ms": 15.0,
            "passed": stats["p95"] <= 50.0,
        }

    def benchmark_health_endpoints(self) -> Dict[str, Any]:
        """Measure latency of shallow and deep health check probes."""
        logger.info("-> Benchmarking Health Probes (/api/health and /api/health/deep)...")

        def _shallow_health():
            res = self.client.get("/api/health")
            assert res.status_code == 200

        def _deep_health():
            res = self.client.get("/api/health/deep")
            assert res.status_code in (200, 503)

        shallow_stats, shallow_qps = measure_block(_shallow_health, iterations=self.iterations)
        deep_stats, deep_qps = measure_block(_deep_health, iterations=max(5, self.iterations // 2))

        return {
            "shallow": {
                "name": "GET /api/health",
                "stats_ms": shallow_stats,
                "throughput_qps": shallow_qps,
                "target_sla_ms": 50.0,
                "passed": shallow_stats["p95"] <= 100.0,
            },
            "deep": {
                "name": "GET /api/health/deep",
                "stats_ms": deep_stats,
                "throughput_qps": deep_qps,
                "target_sla_ms": 250.0,
                "passed": deep_stats["p95"] <= 500.0,
            },
        }

    def benchmark_scoring_engine(self) -> Dict[str, Any]:
        """Measure compute latency for Module 8 5-factor product attractiveness scoring."""
        logger.info("-> Benchmarking Module 8 Scoring Engine...")
        engine = Module8ScoringEngine()

        def _score_single_product():
            engine.score_product(
                product_id="SKU-BENCH-001",
                product_name="Benchmark Product Item",
                category="Beverages",
                shelf_category="bottom",
                total_viewers=45,
                total_passersby=150,
                total_attention_duration_sec=320.0,
                total_interactions=25,
                total_pickups=18,
                total_returns=4,
                total_purchases=12,
                repeat_interactions=6,
                unique_shoppers=40,
                shelf_viewers=45,
                shelf_passersby=150,
            )

        stats, qps = measure_block(_score_single_product, iterations=self.iterations * 2)
        return {
            "name": "Module 8 Attractiveness Scoring (Per SKU)",
            "stats_ms": stats,
            "throughput_qps": qps,
            "target_sla_ms": 5.0,
            "passed": stats["p95"] <= 15.0,
        }

    def benchmark_recommendation_and_simulator(self) -> Dict[str, Any]:
        """Measure compute latency for Module 9 rule engine and planogram simulator."""
        logger.info("-> Benchmarking Module 9 Recommendation & Simulator...")
        rec_engine = Module9RecommendationEngine()
        sample_profiles = [
            {
                "product_id": f"SKU-{i:03d}",
                "product_name": f"Product Sample {i}",
                "category": "Packaged Goods",
                "intrinsic_attractiveness_score": 75.0 if i % 2 == 0 else 30.0,
                "attractiveness_score": 35.0 if i % 2 == 0 else 30.0,
                "shelf_visibility": {"shelf_tier": "BOTTOM" if i % 2 == 0 else "EYE_LEVEL", "gamma_coefficient": 0.40 if i % 2 == 0 else 1.0},
                "pillar_scores": {"interaction_score": 0.5, "pickup_score": 0.4},
                "total_viewers": 30,
                "total_passersby": 100,
                "average_attention_duration_sec": 6.0,
                "total_pickups": 10,
                "total_returns": 2,
                "total_purchases": 8,
                "conversion_potential_score": 70.0,
                "marketing_effectiveness_score": 65.0,
            }
            for i in range(10)
        ]

        def _rec_generation():
            rec_engine.generate_recommendations(sample_profiles)

        def _simulator_run():
            sim_req = PlanogramSimulationRequest(
                product_id="SKU-000",
                current_shelf_tier="BOTTOM",
                target_shelf_tier="EYE_LEVEL",
                current_attractiveness_score=35.0,
                current_intrinsic_score=75.0,
            )
            PlanogramSimulator.simulate(sim_req)

        rec_stats, rec_qps = measure_block(_rec_generation, iterations=self.iterations)
        sim_stats, sim_qps = measure_block(_simulator_run, iterations=self.iterations * 3)

        return {
            "recommendations": {
                "name": "Module 9 Recommendation Generation (10 SKUs)",
                "stats_ms": rec_stats,
                "throughput_qps": rec_qps,
                "target_sla_ms": 25.0,
                "passed": rec_stats["p95"] <= 50.0,
            },
            "simulator": {
                "name": "Module 9 What-If Planogram Simulator",
                "stats_ms": sim_stats,
                "throughput_qps": sim_qps,
                "target_sla_ms": 2.0,
                "passed": sim_stats["p95"] <= 10.0,
            },
        }

    def benchmark_report_exporters(self) -> Dict[str, Any]:
        """Measure rendering throughput for PDF vector docs, Excel workbooks, and CSVs."""
        logger.info("-> Benchmarking Module 12 Export Engines (PDF, Excel, CSV)...")
        with SessionLocal() as db:
            aggregator = RetailIntelligenceAggregator(db)
            report_data = aggregator.compile_report(report_type="consumer_attention")

        pdf_gen = ReportPDFGenerator()
        excel_gen = ReportExcelGenerator()
        csv_gen = ReportCSVGenerator()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            def _export_pdf():
                p = tmp_path / f"bench_{uuid.uuid4().hex[:6]}.pdf"
                pdf_gen.generate_pdf(report_data, p)
                if p.exists():
                    os.remove(p)

            def _export_excel():
                p = tmp_path / f"bench_{uuid.uuid4().hex[:6]}.xlsx"
                excel_gen.generate_excel(report_data, p)
                if p.exists():
                    os.remove(p)

            def _export_csv():
                p = tmp_path / f"bench_{uuid.uuid4().hex[:6]}.csv"
                csv_gen.generate_csv(report_data, p)
                if p.exists():
                    os.remove(p)

            pdf_stats, pdf_qps = measure_block(_export_pdf, iterations=max(5, self.iterations // 3))
            excel_stats, excel_qps = measure_block(_export_excel, iterations=max(5, self.iterations // 3))
            csv_stats, csv_qps = measure_block(_export_csv, iterations=self.iterations)

        return {
            "pdf": {
                "name": "Module 12 PDF Vector Dossier Generation",
                "stats_ms": pdf_stats,
                "throughput_qps": pdf_qps,
                "target_sla_ms": 800.0,
                "passed": pdf_stats["p95"] <= 2000.0,
            },
            "excel": {
                "name": "Module 12 Multi-Tab Excel Workbook Generation",
                "stats_ms": excel_stats,
                "throughput_qps": excel_qps,
                "target_sla_ms": 250.0,
                "passed": excel_stats["p95"] <= 1000.0,
            },
            "csv": {
                "name": "Module 12 Tabular CSV Generation",
                "stats_ms": csv_stats,
                "throughput_qps": csv_qps,
                "target_sla_ms": 10.0,
                "passed": csv_stats["p95"] <= 50.0,
            },
        }

    def run_all(self) -> Dict[str, Any]:
        """Execute full benchmark suite and summarize results."""
        logger.info("\n" + "=" * 70)
        logger.info("   CONSUMER ATTENTION MAPPING SYSTEM (CAMS) BENCHMARK SUITE")
        logger.info("=" * 70 + "\n")

        self.results["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.results["iterations"] = self.iterations
        self.results["database"] = self.benchmark_database_query_pool()
        self.results["health"] = self.benchmark_health_endpoints()
        self.results["scoring"] = self.benchmark_scoring_engine()
        self.results["recommendations"] = self.benchmark_recommendation_and_simulator()
        self.results["reports"] = self.benchmark_report_exporters()

        self._print_summary_table()
        return self.results

    def _print_summary_table(self) -> None:
        """Format and print benchmark results into a clean terminal report."""
        items: List[Dict[str, Any]] = [
            self.results["database"],
            self.results["health"]["shallow"],
            self.results["health"]["deep"],
            self.results["scoring"],
            self.results["recommendations"]["recommendations"],
            self.results["recommendations"]["simulator"],
            self.results["reports"]["pdf"],
            self.results["reports"]["excel"],
            self.results["reports"]["csv"],
        ]

        logger.info("\n" + "-" * 88)
        logger.info(f"{'Component / Subsystem Target':<45} | {'p50':>8} | {'p95':>8} | {'QPS':>7} | {'Status'}")
        logger.info("-" * 88)

        all_passed = True
        for item in items:
            name = item["name"]
            p50 = f"{item['stats_ms']['p50']:.1f}ms"
            p95 = f"{item['stats_ms']['p95']:.1f}ms"
            qps = f"{item['throughput_qps']:.1f}"
            passed = item["passed"]
            if not passed:
                all_passed = False
            badge = "[ PASS ]" if passed else "[ WARN ]"
            logger.info(f"{name:<45} | {p50:>8} | {p95:>8} | {qps:>7} | {badge}")

        logger.info("-" * 88)
        overall_badge = "ALL PERFORMANCE BENCHMARKS SATISFIED [PASS]" if all_passed else "BENCHMARK PERFORMANCE WARNED"
        logger.info(f"\nResult: {overall_badge}\n")


# ── Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CAMS System Performance Benchmark")
    parser.add_argument("--iterations", type=int, default=25, help="Number of benchmark iterations per test")
    parser.add_argument("--output-json", type=str, default=None, help="Optional output JSON file path")
    args = parser.parse_args()

    suite = CAMSBenchmarkSuite(iterations=args.iterations)
    results = suite.run_all()

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Detailed benchmark metrics written to {out_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
