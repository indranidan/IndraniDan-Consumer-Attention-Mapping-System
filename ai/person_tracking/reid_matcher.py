"""
Person Tracking — Lightweight Re-ID Appearance Matcher
======================================================
Provides appearance-based feature extraction and cosine similarity matching
to recover lost customer tracks across occlusions and prevent ID switches.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("reid_matcher")


class AppearanceFeatureExtractor:
    """Extracts a normalized multi-strip color appearance signature from a person crop."""

    def __init__(self, num_vertical_strips: int = 3, bins_per_channel: int = 16):
        self.num_vertical_strips = num_vertical_strips
        self.bins_per_channel = bins_per_channel

    def extract(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a normalized HSV color signature split into vertical strips (head, torso, legs).
        """
        if crop is None or crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
            return None

        try:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            h, w = hsv.shape[:2]
            strip_height = h // self.num_vertical_strips
            strip_features = []

            for i in range(self.num_vertical_strips):
                y_start = i * strip_height
                y_end = (i + 1) * strip_height if i < self.num_vertical_strips - 1 else h
                strip = hsv[y_start:y_end, :]

                # Compute 2D Hue-Saturation Histogram
                hist = cv2.calcHist(
                    [strip],
                    [0, 1],
                    None,
                    [self.bins_per_channel, self.bins_per_channel],
                    [0, 180, 0, 256],
                )
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
                strip_features.append(hist.flatten())

            feat_vector = np.concatenate(strip_features)
            norm = np.linalg.norm(feat_vector)
            if norm > 0:
                feat_vector = feat_vector / norm
            return feat_vector
        except Exception as e:
            logger.debug(f"Failed to extract appearance feature: {e}")
            return None


class ReIDMatcher:
    """Maintains a gallery of track appearance signatures and matches lost tracks."""

    def __init__(
        self,
        similarity_threshold: float = 0.72,
        max_lost_age_frames: int = 90,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_lost_age_frames = max_lost_age_frames
        self.extractor = AppearanceFeatureExtractor()
        self.gallery: Dict[int, Dict[str, Any]] = {}

    def update_track(self, track_id: int, frame: np.ndarray, bbox: Tuple[int, int, int, int], frame_idx: int) -> None:
        """Update or register an active track with its latest appearance crop."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 > x1 and y2 > y1:
            crop = frame[y1:y2, x1:x2]
            feat = self.extractor.extract(crop)
            if feat is not None:
                if track_id in self.gallery:
                    # Exponential moving average feature update
                    prev_feat = self.gallery[track_id]["feature"]
                    updated_feat = 0.8 * prev_feat + 0.2 * feat
                    norm = np.linalg.norm(updated_feat)
                    if norm > 0:
                        updated_feat = updated_feat / norm
                    self.gallery[track_id]["feature"] = updated_feat
                    self.gallery[track_id]["last_frame"] = frame_idx
                    self.gallery[track_id]["last_bbox"] = bbox
                else:
                    self.gallery[track_id] = {
                        "feature": feat,
                        "last_frame": frame_idx,
                        "last_bbox": bbox,
                        "is_lost": False,
                    }

    def mark_lost(self, track_id: int, frame_idx: int) -> None:
        """Mark a track as temporarily lost/occluded."""
        if track_id in self.gallery:
            self.gallery[track_id]["is_lost"] = True
            self.gallery[track_id]["lost_since"] = frame_idx

    def match_candidate(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        frame_idx: int,
        max_center_distance: float = 200.0,
    ) -> Optional[int]:
        """
        Attempt to match an unconfirmed detection against lost tracks in the gallery.
        Returns matching track_id if similarity and spatial gating pass.
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        feat = self.extractor.extract(crop)
        if feat is None:
            return None

        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        best_match_id = None
        best_similarity = self.similarity_threshold

        for track_id, info in list(self.gallery.items()):
            # Check if track is lost and within age limit
            age = frame_idx - info["last_frame"]
            if age > self.max_lost_age_frames:
                # Cleanup expired track from gallery
                continue

            if not info.get("is_lost", False):
                continue

            # Spatial distance gating
            last_bbox = info["last_bbox"]
            lcx, lcy = (last_bbox[0] + last_bbox[2]) / 2.0, (last_bbox[1] + last_bbox[3]) / 2.0
            dist = np.hypot(cx - lcx, cy - lcy)
            if dist > max_center_distance:
                continue

            # Cosine similarity
            gallery_feat = info["feature"]
            similarity = float(np.dot(feat, gallery_feat))

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = track_id

        if best_match_id is not None:
            logger.info(
                f"Re-ID Recovered lost track #{best_match_id} (similarity: {best_similarity:.2f})"
            )
            self.gallery[best_match_id]["is_lost"] = False
            self.gallery[best_match_id]["last_frame"] = frame_idx
            self.gallery[best_match_id]["last_bbox"] = bbox
            return best_match_id

        return None
