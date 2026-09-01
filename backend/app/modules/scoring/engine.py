"""
Module 8 — Product Attractiveness Scoring Engine
==================================================
Core scoring engine that:
1. Ingests Module 3 tracking, Module 4 attention, and Module 5 interaction telemetry
2. Normalizes raw metrics against foot-traffic exposure opportunities
3. Applies Empirical Bayes shrinkage for cold-start / low-sample SKUs
4. Computes shelf tier visibility degradation bias corrections
5. Outputs 5-pillar score vectors (Attractiveness, Visibility, Engagement,
   Conversion Potential, Marketing Effectiveness)

Reuses existing Module 3/4/5 pipeline outputs without re-running YOLO or ByteTrack.
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


class Module8ScoringEngine:
    """
    Dedicated Product Attractiveness Scoring Engine for Module 8.

    Mathematical formulation:
        Attractiveness = 0.35·S_att + 0.25·S_int + 0.20·S_pickup + 0.15·S_conv + 0.05·S_repeat

    Where each S_i is a normalized [0,1] sub-score computed using continuous
    monotonic response functions with Bayesian smoothing.
    """

    # ── Default Hyperparameters ────────────────────────────────────
    ATTENTION_TAU: float = 4.0       # Exponential saturation benchmark (seconds)
    INTERACTION_CAP: float = 2.0     # Max interactions-per-viewer for normalization
    BAYES_ALPHA_PICKUP: float = 1.0  # Beta prior α for pickup rate
    BAYES_BETA_PICKUP: float = 4.0   # Beta prior β for pickup rate
    BAYES_ALPHA_CONV: float = 0.5    # Beta prior α for conversion rate
    BAYES_BETA_CONV: float = 5.0     # Beta prior β for conversion rate
    CONFIDENCE_THRESHOLD: int = 10   # Sample size threshold for confidence calc
    EPSILON: float = 1e-9            # Small constant to avoid division by zero

    def __init__(
        self,
        attention_tau: float = 4.0,
        interaction_cap: float = 2.0,
        confidence_threshold: int = 10,
        logger: Optional[logging.Logger] = None,
    ):
        self.attention_tau = attention_tau
        self.interaction_cap = interaction_cap
        self.confidence_threshold = confidence_threshold
        self.logger = logger or logging.getLogger("module8_engine")

    # ── Sub-Score Computation ──────────────────────────────────────

    def compute_attention_score(self, avg_view_duration_sec: float) -> float:
        """
        Exponential saturation: S_att = 1 - exp(-T_avg / tau)
        4s average → ~63%, 8s → ~86%, 12s → ~95%.
        """
        if avg_view_duration_sec <= 0:
            return 0.0
        return 1.0 - math.exp(-avg_view_duration_sec / self.attention_tau)

    def compute_interaction_score(
        self, total_interactions: int, unique_viewers: int
    ) -> float:
        """
        Rate-capped linear: S_int = min(1.0, interactions / (viewers × cap)).
        """
        if unique_viewers <= 0:
            return 0.0
        raw = total_interactions / (unique_viewers * self.interaction_cap)
        return min(1.0, max(0.0, raw))

    def compute_pickup_score(
        self,
        pickups: int,
        viewers: int,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
    ) -> float:
        """
        Bayesian smoothed pickup rate:
        S_pickup = (pickups + α) / (viewers + α + β)
        """
        a = alpha if alpha is not None else self.BAYES_ALPHA_PICKUP
        b = beta if beta is not None else self.BAYES_BETA_PICKUP
        return (pickups + a) / (viewers + a + b + self.EPSILON)

    def compute_conversion_score(
        self,
        purchases: int,
        pickups: int,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
    ) -> float:
        """
        Bayesian smoothed conversion rate:
        S_conv = (purchases + α) / (max(1, pickups) + α + β)
        """
        a = alpha if alpha is not None else self.BAYES_ALPHA_CONV
        b = beta if beta is not None else self.BAYES_BETA_CONV
        denom = max(1, pickups) + a + b
        return (purchases + a) / (denom + self.EPSILON)

    def compute_repeat_score(
        self, repeat_interactions: int, unique_shoppers: int
    ) -> float:
        """
        Hyperbolic tangent saturation:
        S_repeat = tanh(repeat / max(1, unique_shoppers))
        """
        if unique_shoppers <= 0:
            return 0.0
        return math.tanh(repeat_interactions / max(1, unique_shoppers))

    # ── Shelf Visibility ───────────────────────────────────────────

    def classify_shelf_tier(self, shelf_category: Optional[str] = None) -> ShelfTier:
        """
        Classify shelf tier from category string or position metadata.
        Falls back to UNKNOWN if not determinable.
        """
        if not shelf_category:
            return ShelfTier.UNKNOWN
        cat_lower = shelf_category.lower()
        if "eye" in cat_lower or "hero" in cat_lower:
            return ShelfTier.EYE_LEVEL
        elif "top" in cat_lower or "stretch" in cat_lower:
            return ShelfTier.TOP
        elif "touch" in cat_lower or "chest" in cat_lower or "mid" in cat_lower:
            return ShelfTier.TOUCH
        elif "bottom" in cat_lower or "stoop" in cat_lower or "floor" in cat_lower:
            return ShelfTier.BOTTOM
        return ShelfTier.UNKNOWN

    def compute_shelf_visibility(
        self,
        shelf_id: str,
        shelf_name: str,
        shelf_tier: ShelfTier,
        shelf_viewers: int = 0,
        shelf_passersby: int = 0,
    ) -> ShelfVisibilityProfile:
        """Compute shelf visibility score from tier and traffic data."""
        gamma = SHELF_TIER_GAMMA.get(shelf_tier, 0.75)
        # Visibility score = gamma × engagement_ratio (0-100)
        engagement_ratio = shelf_viewers / max(1, shelf_passersby)
        visibility_score = min(100.0, gamma * engagement_ratio * 100.0)
        return ShelfVisibilityProfile(
            shelf_id=shelf_id,
            shelf_name=shelf_name,
            shelf_tier=shelf_tier,
            gamma_coefficient=gamma,
            visibility_score=round(visibility_score, 2),
        )

    def compute_intrinsic_attractiveness(
        self, observed_score: float, gamma: float
    ) -> float:
        """
        Decouple shelf placement bias from intrinsic product appeal:
        Intrinsic = min(100.0, Observed / max(0.2, gamma))
        """
        return min(100.0, observed_score / max(0.2, gamma))

    # ── Confidence ─────────────────────────────────────────────────

    def compute_confidence(self, sample_size: int) -> ScoringConfidence:
        """Compute sample-size confidence rating."""
        return ScoringConfidence.compute(sample_size, self.confidence_threshold)

    # ── Master Scoring Pipeline ────────────────────────────────────

    def score_product(
        self,
        product_id: str,
        product_name: str,
        sku: Optional[str] = None,
        category: Optional[str] = None,
        shelf_id: Optional[str] = None,
        shelf_name: Optional[str] = None,
        shelf_category: Optional[str] = None,
        total_viewers: int = 0,
        total_passersby: int = 0,
        total_attention_duration_sec: float = 0.0,
        total_interactions: int = 0,
        total_pickups: int = 0,
        total_returns: int = 0,
        total_purchases: int = 0,
        repeat_interactions: int = 0,
        unique_shoppers: int = 0,
        shelf_viewers: int = 0,
        shelf_passersby: int = 0,
    ) -> ProductScoreProfile:
        """
        Compute complete Module 8 score profile for a single product.

        Parameters
        ----------
        All raw telemetry counters from Modules 3, 4, and 5.

        Returns
        -------
        ProductScoreProfile with all 5 pillar scores, shelf visibility,
        confidence rating, and qualitative grade.
        """
        # Average attention duration per viewer
        avg_attn = (
            total_attention_duration_sec / max(1, total_viewers)
            if total_viewers > 0
            else 0.0
        )

        # 1. Compute 5 sub-scores
        s_att = self.compute_attention_score(avg_attn)
        s_int = self.compute_interaction_score(total_interactions, total_viewers)
        s_pickup = self.compute_pickup_score(total_pickups, total_viewers)
        s_conv = self.compute_conversion_score(total_purchases, total_pickups)
        s_repeat = self.compute_repeat_score(repeat_interactions, unique_shoppers)

        pillar = PillarScores(
            attention_score=s_att,
            interaction_score=s_int,
            pickup_score=s_pickup,
            conversion_score=s_conv,
            repeat_score=s_repeat,
        )

        attractiveness = pillar.composite_score
        rating = pillar.rating

        # 2. Shelf visibility
        shelf_tier = self.classify_shelf_tier(shelf_category)
        visibility = self.compute_shelf_visibility(
            shelf_id=shelf_id or "",
            shelf_name=shelf_name or "",
            shelf_tier=shelf_tier,
            shelf_viewers=shelf_viewers,
            shelf_passersby=shelf_passersby,
        )

        # 3. Intrinsic attractiveness (tier-adjusted)
        intrinsic = self.compute_intrinsic_attractiveness(
            attractiveness, visibility.gamma_coefficient
        )

        # 4. Engagement score (interaction + attention combined, 0-100)
        engagement = min(100.0, (s_att * 60.0 + s_int * 40.0))

        # 5. Conversion potential (pickup + conversion combined, 0-100)
        conversion_potential = min(100.0, (s_pickup * 55.0 + s_conv * 45.0))

        # 6. Marketing effectiveness (comparison to category baseline, simplified)
        # For now, uses the composite vs a neutral 50.0 baseline
        marketing_eff = min(100.0, max(0.0, attractiveness * 1.2))

        # 7. Confidence
        confidence = self.compute_confidence(total_viewers)

        return ProductScoreProfile(
            product_id=product_id,
            product_name=product_name,
            sku=sku,
            category=category,
            shelf_id=shelf_id,
            shelf_name=shelf_name,
            total_viewers=total_viewers,
            total_passersby=total_passersby,
            total_attention_duration_sec=total_attention_duration_sec,
            average_attention_duration_sec=round(avg_attn, 3),
            total_interactions=total_interactions,
            total_pickups=total_pickups,
            total_returns=total_returns,
            total_purchases=total_purchases,
            repeat_interactions=repeat_interactions,
            unique_shoppers=unique_shoppers,
            pillar_scores=pillar,
            shelf_visibility=visibility,
            confidence=confidence,
            attractiveness_score=attractiveness,
            intrinsic_attractiveness_score=round(intrinsic, 2),
            engagement_score=round(engagement, 2),
            conversion_potential_score=round(conversion_potential, 2),
            marketing_effectiveness_score=round(marketing_eff, 2),
            rating=rating,
        )

    # ── Batch Job Processing ───────────────────────────────────────

    def process_completed_job(
        self,
        job_output_dir: Path,
        configured_products: Optional[List[Dict[str, Any]]] = None,
        configured_shelves: Optional[List[Dict[str, Any]]] = None,
        store_id: Optional[str] = None,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Score all products for a completed AI job using Module 3/4/5 outputs.

        Parameters
        ----------
        job_output_dir : Path
            Path to the job output directory (e.g. outputs/ai_jobs/{job_id}).
        configured_products : list
            Products from DB with fields: id, name, sku, shelf_id, category.
        configured_shelves : list
            Shelves from DB with fields: id, name, shelf_code, category.

        Returns
        -------
        dict with keys: summary, products, scored_profiles.
        """
        configured_products = configured_products or []
        configured_shelves = configured_shelves or []

        # Load upstream telemetry
        m4_data = self._load_module4_data(job_output_dir)
        m5_data = self._load_module5_data(job_output_dir)
        m3_data = self._load_module3_data(job_output_dir)

        # Build shelf lookup
        shelf_lookup: Dict[str, Dict[str, Any]] = {}
        for s in configured_shelves:
            sid = str(s.get("id", ""))
            shelf_lookup[sid] = s

        # Compute total footfall from tracking data
        total_footfall = m3_data.get("total_unique_shoppers", 0)

        # Build shelf-to-product counts for equal distribution (Task 3.1)
        shelf_product_counts: Dict[str, int] = {}
        for prod in configured_products:
            p_shelf_id = str(prod.get("shelf_id", ""))
            if p_shelf_id:
                shelf_product_counts[p_shelf_id] = shelf_product_counts.get(p_shelf_id, 0) + 1

        # Score each product
        profiles: List[ProductScoreProfile] = []
        for prod in configured_products:
            pid = str(prod.get("id", ""))
            pname = prod.get("name", "Unknown")
            psku = prod.get("sku")
            pcategory = prod.get("category")
            p_shelf_id = str(prod.get("shelf_id", ""))

            shelf_info = shelf_lookup.get(p_shelf_id, {})
            shelf_name = shelf_info.get("name", "") or prod.get("shelf_name", "")
            shelf_code = shelf_info.get("shelf_code", "")
            shelf_cat = shelf_info.get("category", "") or prod.get("shelf_category", "")

            # Extract product telemetry from M4/M5 data
            m4_product = m4_data.get("products", {}).get(pid, {})
            m5_product = m5_data.get("products", {}).get(pid, {})

            viewers = m4_product.get("viewers", 0) or m5_product.get("unique_viewers", 0)
            attn_dur = m4_product.get("total_focus_duration_sec", 0.0)
            interactions = (
                m5_product.get("views", 0)
                + m5_product.get("pickup_events", 0)
                + m5_product.get("comparison_events", 0)
            )
            pickups = m5_product.get("pickup_events", 0)
            returns = m5_product.get("return_events", 0)
            purchases = m5_product.get("purchase_count", 0)
            repeats = m5_product.get("repeat_interactions", 0)
            unique_shop = m5_product.get("unique_viewers", 0) or viewers

            # Robust M4 shelf resolution (checks ID, shelf_code, name, and normalized keys)
            m4_shelves = m4_data.get("shelves", {})
            m4_shelf = (
                m4_shelves.get(p_shelf_id)
                or (shelf_code and m4_shelves.get(shelf_code))
                or (shelf_name and m4_shelves.get(shelf_name))
                or (shelf_name and m4_shelves.get(shelf_name.lower().replace(" ", "_")))
                or {}
            )

            # Task 3.2: Distribute shelf-level M4 attention to products
            # when per-product telemetry is empty
            if not m4_product and m4_shelf and (p_shelf_id or shelf_name):
                n_products = max(1, shelf_product_counts.get(p_shelf_id, 1))
                shelf_v = m4_shelf.get("viewers", 0)
                shelf_attn = m4_shelf.get("shelf_attention_time_sec", 0.0)
                if shelf_v > 0:
                    viewers = max(viewers, int(shelf_v / n_products) or 1)
                if shelf_attn > 0:
                    attn_dur = max(attn_dur, shelf_attn / n_products)
                if unique_shop == 0:
                    unique_shop = viewers

            # Task 3.3: Distribute shelf-level M5 interactions to products
            # when per-product interaction telemetry is all-zero
            m5_product_is_zero = (
                m5_product.get("views", 0) == 0
                and m5_product.get("unique_viewers", 0) == 0
            )
            if m5_product_is_zero:
                m5_summary = m5_data.get("summary", {})
                if m4_shelf.get("viewers", 0) > 0:
                    n_products = max(1, shelf_product_counts.get(p_shelf_id, 1))
                    distributed_views = max(1, int(m4_shelf.get("viewers", 0) / n_products))
                    interactions = max(interactions, distributed_views)
                    if viewers == 0:
                        viewers = max(1, distributed_views)
                    if unique_shop == 0:
                        unique_shop = viewers
                elif m5_summary.get("total_views", 0) > 0:
                    total_prods = max(1, len(configured_products))
                    distributed_views = max(0, int(m5_summary.get("total_views", 0) / total_prods))
                    if distributed_views > 0:
                        interactions = max(interactions, distributed_views)
                    distributed_dur = m5_summary.get("total_view_duration_sec", 0.0) / total_prods
                    if attn_dur == 0.0 and distributed_dur > 0:
                        attn_dur = distributed_dur

            shelf_viewers_count = m4_shelf.get("viewers", 0)

            profile = self.score_product(
                product_id=pid,
                product_name=pname,
                sku=psku,
                category=pcategory,
                shelf_id=p_shelf_id,
                shelf_name=shelf_name,
                shelf_category=shelf_cat,
                total_viewers=viewers,
                total_passersby=total_footfall,
                total_attention_duration_sec=attn_dur,
                total_interactions=interactions,
                total_pickups=pickups,
                total_returns=returns,
                total_purchases=purchases,
                repeat_interactions=repeats,
                unique_shoppers=unique_shop,
                shelf_viewers=shelf_viewers_count,
                shelf_passersby=total_footfall,
            )
            profiles.append(profile)

        # Build summary
        summary = self._build_summary(profiles)

        return {
            "summary": summary.to_dict(),
            "products": [p.to_dict() for p in profiles],
            "scored_profiles": profiles,
        }

    def _build_summary(self, profiles: List[ProductScoreProfile]) -> Module8Summary:
        """Build Module8Summary from scored profiles."""
        if not profiles:
            return Module8Summary(insufficient_data=True)

        sorted_profiles = sorted(
            profiles, key=lambda p: p.attractiveness_score, reverse=True
        )
        top = sorted_profiles[0]
        bottom = sorted_profiles[-1]
        avg_score = sum(p.attractiveness_score for p in profiles) / len(profiles)
        avg_conf = sum(p.confidence.confidence_score for p in profiles) / len(profiles)

        # Task 4.2: Flag insufficient data when all products have zero viewers
        all_zero_viewers = all(p.total_viewers == 0 for p in profiles)

        return Module8Summary(
            total_products_scored=len(profiles),
            average_attractiveness_score=round(avg_score, 2),
            top_performer_id=top.product_id,
            top_performer_name=top.product_name,
            top_performer_score=top.attractiveness_score,
            bottom_performer_id=bottom.product_id,
            bottom_performer_name=bottom.product_name,
            bottom_performer_score=bottom.attractiveness_score,
            average_confidence=round(avg_conf, 4),
            insufficient_data=all_zero_viewers,
        )

    # ── Upstream Data Loading ──────────────────────────────────────

    def _load_module4_data(self, output_dir: Path) -> Dict[str, Any]:
        """Load Module 4 attention analysis outputs."""
        result: Dict[str, Any] = {"products": {}, "shelves": {}}

        # Task 2.1: Load from module4/module4_attention_report.json (richer data)
        m4_report_file = output_dir / "module4" / "module4_attention_report.json"
        if m4_report_file.exists():
            try:
                data = json.loads(m4_report_file.read_text(encoding="utf-8"))
                # Parse shelf attention metrics from the shelves array
                for item in data.get("shelves", []):
                    sid = str(item.get("shelf_id", ""))
                    if sid:
                        result["shelves"][sid] = {
                            "viewers": item.get("viewers", 0),
                            "visitors": item.get("visitors", 0),
                            "dwell_time_sec": item.get("dwell_time_sec", 0.0),
                            "shelf_attention_time_sec": item.get("shelf_attention_time_sec", 0.0),
                            "attention_event_count": item.get("attention_event_count", 0),
                        }
            except Exception as exc:
                self.logger.warning(f"Could not load Module 4 report: {exc}")

        # Task 2.2: Also try target attention summary using correct key "targets"
        attn_file = output_dir / "phase5" / "reports" / "target_attention_summary.json"
        if attn_file.exists():
            try:
                data = json.loads(attn_file.read_text(encoding="utf-8"))
                # Parse targets (shelf-level and product-level attention)
                for item in data.get("targets", []):
                    target_type = item.get("target_type", "")
                    target_id = str(item.get("target_id", ""))
                    if not target_id:
                        continue
                    if target_type == "shelf":
                        # Only populate if not already loaded from M4 report
                        if target_id not in result["shelves"]:
                            result["shelves"][target_id] = {
                                "viewers": item.get("unique_shoppers", 0),
                                "visitors": item.get("unique_shoppers", 0),
                                "dwell_time_sec": item.get("total_attention_sec", 0.0),
                                "shelf_attention_time_sec": item.get("total_attention_sec", 0.0),
                                "attention_event_count": item.get("attention_event_count", 0),
                            }
                    elif target_type == "product":
                        pid = target_id
                        if pid not in result["products"]:
                            result["products"][pid] = {
                                "viewers": item.get("unique_shoppers", 0),
                                "total_focus_duration_sec": item.get("total_attention_sec", 0.0),
                                "average_focus_duration_sec": item.get("average_attention_sec", 0.0),
                                "attention_events": item.get("attention_event_count", 0),
                            }
            except Exception as exc:
                self.logger.warning(f"Could not load target attention summary: {exc}")

        return result

    def _load_module5_data(self, output_dir: Path) -> Dict[str, Any]:
        """Load Module 5 product interaction outputs."""
        result: Dict[str, Any] = {"products": {}, "summary": {}}

        # Task 1.1: Use the correct file name produced by the interaction service
        m5_file = output_dir / "module5" / "module5_interaction_report.json"
        if not m5_file.exists():
            # Fallback: legacy file name for backward compatibility
            m5_file = output_dir / "module5" / "module5_analysis.json"
        if not m5_file.exists():
            # Fallback: check disk-cached analysis at root level
            m5_file = output_dir / "module5_analysis.json"

        if m5_file.exists():
            try:
                data = json.loads(m5_file.read_text(encoding="utf-8"))
                result["summary"] = data.get("summary", {})
                for item in data.get("products", []):
                    pid = str(item.get("product_id", ""))
                    if pid:
                        result["products"][pid] = item
            except Exception as exc:
                self.logger.warning(f"Could not load Module 5 data: {exc}")

        return result

    def _load_module3_data(self, output_dir: Path) -> Dict[str, Any]:
        """Load Module 3 tracking/session data for total footfall."""
        result: Dict[str, Any] = {"total_unique_shoppers": 0}

        sessions_file = output_dir / "phase3" / "reports" / "sessions.json"
        if sessions_file.exists():
            try:
                data = json.loads(sessions_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    result["total_unique_shoppers"] = len(data)
                elif isinstance(data, dict):
                    result["total_unique_shoppers"] = data.get(
                        "total_unique_shoppers",
                        len(data.get("sessions", [])),
                    )
            except Exception as exc:
                self.logger.warning(f"Could not load Module 3 data: {exc}")

        return result
