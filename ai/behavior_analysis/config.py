"""
Behavior Analysis — Configuration
=====================================
Configurable thresholds for the Module 6 Consumer Behavior segmentation engine.
All thresholds can be overridden per analysis run.
"""

from dataclasses import dataclass


@dataclass
class BehaviorConfig:
    """Configuration thresholds for behavioral segmentation."""

    # ── Explorer thresholds ─────────────────────────────────────
    explorer_path_efficiency_max: float = 0.40
    explorer_min_zones: int = 3
    explorer_min_duration_sec: float = 45.0

    # ── Quick Buyer thresholds ──────────────────────────────────
    quick_buyer_path_efficiency_min: float = 0.65
    quick_buyer_max_zones: int = 2
    quick_buyer_max_pickup_time_sec: float = 5.0

    # ── Comparison Shopper thresholds ───────────────────────────
    comparison_gaze_alternation_min: float = 2.0
    comparison_min_pickup_return_events: int = 2

    # ── Impulse Buyer thresholds ────────────────────────────────
    impulse_min_promo_deviations: int = 1
    impulse_max_comparison_duration_sec: float = 3.0

    # ── Brand Loyal thresholds ──────────────────────────────────
    brand_loyalty_concentration_min: float = 0.75
    brand_loyalty_max_gaze_alternation: float = 1.0

    # ── General session filters ─────────────────────────────────
    min_session_duration_sec: float = 2.0
    min_session_frames: int = 15

    # ── Funnel & friction thresholds ────────────────────────────
    friction_min_gaze_shoppers: int = 5
    friction_max_interaction_rate: float = 0.20

    # ── Transition matrix ───────────────────────────────────────
    transition_min_sessions: int = 3
