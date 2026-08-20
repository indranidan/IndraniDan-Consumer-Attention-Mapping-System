"""
Module 4 — Attention Analysis Engine Package
"""

from app.module4.engine import Module4AttentionEngine
from app.module4.event_detector import Module4AttentionEventDetector
from app.module4.gaze_estimator import Module4GazeEstimator
from app.module4.head_pose import Module4HeadPoseEstimator
from app.module4.heatmap_generator import Module4HeatmapGenerator
from app.module4.models import (
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
from app.module4.product_attention import Module4ProductAttentionDetector
from app.module4.report_generator import Module4ReportGenerator
from app.module4.shelf_engagement import Module4ShelfEngagementAnalyzer

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
