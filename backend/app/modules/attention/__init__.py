"""
Module 4 — Attention Analysis Engine Package
"""

from app.modules.attention.engine import Module4AttentionEngine
from app.modules.attention.event_detector import Module4AttentionEventDetector
from app.modules.attention.gaze_estimator import Module4GazeEstimator
from app.modules.attention.head_pose import Module4HeadPoseEstimator
from app.modules.attention.heatmap_generator import Module4HeatmapGenerator
from app.modules.attention.models import (
    AttentionDirection,
    AttentionEventRecord,
    AttentionQualityMetrics,
    AttentionState,
    AttentionSubject,
    AttentionType,
    GazeEstimate,
    HeadPoseData,
    Module4Summary,
    ProductAttention,
    ShelfEngagement,
)
from app.modules.attention.product_attention import Module4ProductAttentionDetector
from app.modules.attention.report_generator import Module4ReportGenerator
from app.modules.attention.shelf_engagement import Module4ShelfEngagementAnalyzer

__all__ = [
    "Module4AttentionEngine",
    "Module4HeadPoseEstimator",
    "Module4GazeEstimator",
    "Module4ShelfEngagementAnalyzer",
    "Module4ProductAttentionDetector",
    "Module4AttentionEventDetector",
    "Module4ReportGenerator",
    "Module4HeatmapGenerator",
    "AttentionSubject",
    "HeadPoseData",
    "GazeEstimate",
    "AttentionEventRecord",
    "ShelfEngagement",
    "ProductAttention",
    "AttentionQualityMetrics",
    "Module4Summary",
    "AttentionType",
    "AttentionDirection",
    "AttentionState",
]
