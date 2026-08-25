"""
Module 8 — Product Attractiveness Scoring Engine Unit Tests
============================================================
Verifies:
- 5-factor weighted formula correctness
- Exponential attention saturation response
- Bayesian prior shrinkage for small-sample SKUs
- Shelf tier planogram bias adjustments
- Confidence score computation
- Report generation
"""

import math
import sys
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.scoring.models import (
    ConfidenceLevel,
    Module8Summary,
    PillarScores,
    ProductScoreProfile,
    QualitativeRating,
    ScoringConfidence,
    ShelfTier,
    ShelfVisibilityProfile,
    SHELF_TIER_GAMMA,
)
from app.modules.scoring.engine import Module8ScoringEngine
from app.modules.scoring.report_generator import Module8ReportGenerator


# ── PillarScores Tests ─────────────────────────────────────────────

class TestPillarScores:
    """Tests for the PillarScores composite calculation."""

    def test_zero_scores_give_zero_composite(self):
        p = PillarScores()
        assert p.composite_score == 0.0
        assert p.rating == QualitativeRating.D

    def test_perfect_scores_give_100(self):
        p = PillarScores(
            attention_score=1.0,
            interaction_score=1.0,
            pickup_score=1.0,
            conversion_score=1.0,
            repeat_score=1.0,
        )
        assert p.composite_score == 100.0
        assert p.rating == QualitativeRating.A_PLUS

    def test_weighted_formula_correctness(self):
        """Verify: Score = 0.35×att + 0.25×int + 0.20×pick + 0.15×conv + 0.05×rep × 100"""
        p = PillarScores(
            attention_score=0.6,
            interaction_score=0.4,
            pickup_score=0.3,
            conversion_score=0.2,
            repeat_score=0.1,
        )
        expected = (0.35 * 0.6 + 0.25 * 0.4 + 0.20 * 0.3 + 0.15 * 0.2 + 0.05 * 0.1) * 100
        assert abs(p.composite_score - round(expected, 2)) < 0.01

    def test_rating_bands(self):
        assert QualitativeRating.from_score(95.0) == QualitativeRating.A_PLUS
        assert QualitativeRating.from_score(80.0) == QualitativeRating.A
        assert QualitativeRating.from_score(60.0) == QualitativeRating.B
        assert QualitativeRating.from_score(40.0) == QualitativeRating.C
        assert QualitativeRating.from_score(20.0) == QualitativeRating.D


# ── ScoringEngine Sub-Score Tests ──────────────────────────────────

class TestScoringEngine:
    """Tests for the Module8ScoringEngine scoring functions."""

    def setup_method(self):
        self.engine = Module8ScoringEngine()

    # Attention Score
    def test_attention_zero_duration(self):
        assert self.engine.compute_attention_score(0.0) == 0.0

    def test_attention_4s_benchmark(self):
        """4s average view should yield ~63% (1 - 1/e)."""
        score = self.engine.compute_attention_score(4.0)
        expected = 1.0 - math.exp(-1.0)
        assert abs(score - expected) < 0.001

    def test_attention_monotonically_increasing(self):
        s1 = self.engine.compute_attention_score(2.0)
        s2 = self.engine.compute_attention_score(4.0)
        s3 = self.engine.compute_attention_score(8.0)
        assert s1 < s2 < s3

    # Interaction Score
    def test_interaction_zero_viewers(self):
        assert self.engine.compute_interaction_score(5, 0) == 0.0

    def test_interaction_capped_at_one(self):
        score = self.engine.compute_interaction_score(100, 5)
        assert score == 1.0

    # Pickup Score (Bayesian)
    def test_pickup_bayesian_smoothing_low_sample(self):
        """With 1 pickup from 1 viewer, raw = 1.0 but Bayesian should be < 1.0."""
        raw_rate = 1.0 / 1.0
        bayesian = self.engine.compute_pickup_score(1, 1)
        assert bayesian < raw_rate
        assert bayesian > 0.0

    def test_pickup_large_sample_approaches_raw(self):
        """With many observations, Bayesian rate should approach raw rate."""
        raw_rate = 50 / 100  # 0.5
        bayesian = self.engine.compute_pickup_score(50, 100)
        assert abs(bayesian - raw_rate) < 0.05

    # Conversion Score (Bayesian)
    def test_conversion_cold_start_shrinkage(self):
        """Zero purchases from zero pickups should not give 0 or 1."""
        score = self.engine.compute_conversion_score(0, 0)
        assert 0.0 < score < 1.0

    # Repeat Score
    def test_repeat_zero(self):
        assert self.engine.compute_repeat_score(0, 10) == 0.0

    def test_repeat_saturates(self):
        """High repeat ratio should approach 1.0 via tanh."""
        score = self.engine.compute_repeat_score(100, 10)
        assert score > 0.95

    # Shelf Tier Classification
    def test_shelf_tier_eye_level(self):
        assert self.engine.classify_shelf_tier("Eye Level Display") == ShelfTier.EYE_LEVEL

    def test_shelf_tier_bottom(self):
        assert self.engine.classify_shelf_tier("Bottom Shelf") == ShelfTier.BOTTOM

    def test_shelf_tier_unknown(self):
        assert self.engine.classify_shelf_tier("") == ShelfTier.UNKNOWN
        assert self.engine.classify_shelf_tier(None) == ShelfTier.UNKNOWN

    # Intrinsic Attractiveness
    def test_intrinsic_bottom_tier_amplification(self):
        """A 40/100 product on bottom tier (γ=0.40) should have intrinsic = 100."""
        intrinsic = self.engine.compute_intrinsic_attractiveness(40.0, 0.40)
        assert intrinsic == 100.0

    def test_intrinsic_eye_level_no_change(self):
        """Eye level (γ=1.0) should not change the score."""
        intrinsic = self.engine.compute_intrinsic_attractiveness(60.0, 1.0)
        assert intrinsic == 60.0


# ── Full Product Scoring Integration ───────────────────────────────

class TestProductScoring:
    """Integration tests for score_product()."""

    def setup_method(self):
        self.engine = Module8ScoringEngine()

    def test_score_product_returns_complete_profile(self):
        profile = self.engine.score_product(
            product_id="prod-001",
            product_name="Premium Coffee",
            sku="COF-001",
            category="Beverages",
            total_viewers=20,
            total_passersby=100,
            total_attention_duration_sec=80.0,
            total_interactions=15,
            total_pickups=5,
            total_returns=1,
            total_purchases=3,
            repeat_interactions=4,
            unique_shoppers=18,
        )
        assert profile.product_id == "prod-001"
        assert 0.0 <= profile.attractiveness_score <= 100.0
        assert profile.rating in QualitativeRating
        assert profile.confidence.sample_size == 20
        d = profile.to_dict()
        assert "pillar_scores" in d
        assert "shelf_visibility" in d
        assert "confidence" in d

    def test_zero_telemetry_produces_low_score(self):
        profile = self.engine.score_product(
            product_id="p-empty",
            product_name="No Data Product",
            total_viewers=0,
        )
        assert profile.attractiveness_score < 20.0
        assert profile.confidence.confidence_level == ConfidenceLevel.LOW


# ── Confidence Tests ───────────────────────────────────────────────

class TestConfidence:
    def test_low_sample_confidence(self):
        c = ScoringConfidence.compute(2, threshold=10)
        assert c.confidence_level == ConfidenceLevel.LOW

    def test_high_sample_confidence(self):
        c = ScoringConfidence.compute(100, threshold=10)
        assert c.confidence_level == ConfidenceLevel.HIGH
        assert c.confidence_score > 0.7


# ── Report Generator Tests ─────────────────────────────────────────

class TestReportGenerator:
    def test_json_report_structure(self):
        gen = Module8ReportGenerator()
        summary = Module8Summary(total_products_scored=1)
        profile = ProductScoreProfile(product_id="p1", product_name="Test")
        report = gen.generate_json_report(summary, [profile])
        assert report["module"] == "Module 8 — Product Attractiveness Scoring Engine"
        assert report["total_products_scored"] == 1
        assert len(report["products"]) == 1

    def test_markdown_report_not_empty(self):
        gen = Module8ReportGenerator()
        summary = Module8Summary(total_products_scored=1)
        profile = ProductScoreProfile(product_id="p1", product_name="Test")
        report_data = gen.generate_json_report(summary, [profile])
        md = gen.generate_markdown_report(report_data)
        assert "Module 8" in md
        assert "Leaderboard" in md
