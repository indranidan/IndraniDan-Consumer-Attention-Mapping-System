"""
Movement Analysis — Path Tracker
===================================
Maintains chronological movement paths for every tracked shopper.
Stores center-point positions per frame for both visualization
(bounded deque) and complete reporting (append-only list).
"""

import logging
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ai.logger import setup_logger


@dataclass
class PathPoint:
    """A single position sample in a shopper's movement path."""

    frame: int
    timestamp: float
    x: int
    y: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            "frame": self.frame,
            "timestamp": round(self.timestamp, 3),
            "x": self.x,
            "y": self.y,
        }


class ShopperPath:
    """
    Manages the movement path history for a single tracked shopper.

    Maintains two storage mechanisms:
    - A bounded deque for visualization (recent N points)
    - An append-only list for complete path reporting
    """

    def __init__(self, track_id: int, history_length: int = 100):
        """
        Initialize shopper path storage.

        Parameters
        ----------
        track_id : int
            Persistent tracking ID from ByteTrack.
        history_length : int
            Maximum number of recent points to keep for visualization.
        """
        self.track_id = track_id
        self.history_length = history_length

        # Bounded deque for visualization (recent points only)
        self._visualization_points: deque = deque(maxlen=history_length)

        # Complete path for final report export (lightweight — only coordinates)
        self._full_path: List[PathPoint] = []

    def add_point(
        self, frame: int, timestamp: float, x: int, y: int
    ) -> None:
        """
        Record a new position sample.

        Parameters
        ----------
        frame : int
            Frame number (1-indexed).
        timestamp : float
            Video timestamp in seconds.
        x : int
            Center X coordinate.
        y : int
            Center Y coordinate.
        """
        point = PathPoint(frame=frame, timestamp=timestamp, x=x, y=y)

        self._visualization_points.append((x, y))
        self._full_path.append(point)

    def get_visualization_points(self) -> List[Tuple[int, int]]:
        """
        Return recent path points for on-frame visualization.

        Returns
        -------
        List[Tuple[int, int]]
            List of (x, y) coordinate tuples.
        """
        return list(self._visualization_points)

    def get_full_path(self) -> List[PathPoint]:
        """
        Return the complete path history for reporting.

        Returns
        -------
        List[PathPoint]
            All recorded path points in chronological order.
        """
        return list(self._full_path)

    def get_full_path_dicts(self) -> List[Dict]:
        """
        Return the complete path as a list of dictionaries.

        Returns
        -------
        List[Dict]
            All path points as dictionaries for JSON export.
        """
        return [p.to_dict() for p in self._full_path]

    @property
    def total_points(self) -> int:
        """Total number of path points recorded."""
        return len(self._full_path)

    @property
    def first_point(self) -> Optional[PathPoint]:
        """Return the first recorded path point, or None."""
        return self._full_path[0] if self._full_path else None

    @property
    def last_point(self) -> Optional[PathPoint]:
        """Return the most recent path point, or None."""
        return self._full_path[-1] if self._full_path else None


class PathTracker:
    """
    Manages path tracking for all active shoppers.

    Creates and updates ShopperPath instances for each unique tracking ID.
    """

    def __init__(
        self,
        history_length: int = 100,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the path tracker.

        Parameters
        ----------
        history_length : int
            Maximum visualization history length per shopper.
        logger : logging.Logger, optional
            Logger instance.
        """
        self.history_length = history_length
        self.logger = logger or setup_logger("path_tracker")
        self._paths: Dict[int, ShopperPath] = {}

    def update(
        self,
        track_id: int,
        frame: int,
        timestamp: float,
        center_x: int,
        center_y: int,
    ) -> None:
        """
        Record a position for a tracked shopper.

        Creates a new ShopperPath if this is the first detection of the track_id.

        Parameters
        ----------
        track_id : int
            Persistent tracking ID.
        frame : int
            Current frame number.
        timestamp : float
            Current video timestamp in seconds.
        center_x : int
            Bounding box center X coordinate.
        center_y : int
            Bounding box center Y coordinate.
        """
        if track_id not in self._paths:
            self._paths[track_id] = ShopperPath(
                track_id=track_id,
                history_length=self.history_length,
            )

        self._paths[track_id].add_point(
            frame=frame, timestamp=timestamp, x=center_x, y=center_y
        )

    def get_path(self, track_id: int) -> Optional[ShopperPath]:
        """
        Retrieve the path for a specific tracking ID.

        Parameters
        ----------
        track_id : int
            Tracking ID.

        Returns
        -------
        Optional[ShopperPath]
            Shopper's path, or None if not tracked.
        """
        return self._paths.get(track_id)

    def get_all_paths(self) -> Dict[int, ShopperPath]:
        """Return all tracked paths."""
        return dict(self._paths)

    def get_all_paths_dicts(self) -> Dict[str, List[Dict]]:
        """
        Return all paths as a dictionary of lists, keyed by track_id string.

        Returns
        -------
        Dict[str, List[Dict]]
            Path data suitable for JSON export.
        """
        return {
            str(track_id): path.get_full_path_dicts()
            for track_id, path in sorted(self._paths.items())
        }
