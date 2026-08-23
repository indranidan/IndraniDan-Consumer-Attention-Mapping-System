"""
Movement Analysis — Zone Manager
===================================
Loads zone and entry/exit region definitions from a JSON configuration file.
Provides polygon-based spatial queries using OpenCV's pointPolygonTest.
Validates polygon geometry and detects overlapping zone warnings.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import cv2
import numpy as np

from ai.logger import setup_logger


@dataclass
class ZoneDefinition:
    """A named spatial zone defined by a polygon."""

    id: str
    name: str
    polygon: List[Tuple[int, int]]
    raw_polygon: List[Tuple[float, float]] = field(default_factory=list)
    is_normalized: bool = False
    _contour: Optional[np.ndarray] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Pre-compute the OpenCV contour array for point-in-polygon tests."""
        if not self.raw_polygon:
            self.raw_polygon = [(float(p[0]), float(p[1])) for p in self.polygon]
        self._recompute_contour()

    def _recompute_contour(self) -> None:
        """Recompute the OpenCV contour from the current polygon vertices."""
        self._contour = np.array(self.polygon, dtype=np.int32).reshape((-1, 1, 2))

    @property
    def contour(self) -> np.ndarray:
        """Return the pre-computed OpenCV contour for this zone polygon."""
        return self._contour

    def scale_to_frame(self, width: int, height: int) -> None:
        """Scale polygon coordinates from normalized (0-1) to pixel space."""
        if self.is_normalized and width > 0 and height > 0:
            self.polygon = [
                (int(round(p[0] * width)), int(round(p[1] * height)))
                for p in self.raw_polygon
            ]
            self._recompute_contour()


class ZoneManager:
    """
    Manages spatial zone definitions, entry regions, and exit regions.

    Loads polygon configurations from a JSON file and provides efficient
    point-in-polygon queries using cv2.pointPolygonTest.
    Supports both absolute pixel coordinates and normalized (0.0 - 1.0) coordinates.
    """

    def __init__(
        self,
        config_path: Path,
        frame_size: Optional[Tuple[int, int]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the zone manager.

        Parameters
        ----------
        config_path : Path
            Path to the zones.json configuration file.
        frame_size : Tuple[int, int], optional
            (width, height) to scale normalized coordinates immediately.
        logger : logging.Logger, optional
            Logger instance.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        ValueError
            If the configuration is invalid or contains invalid polygons.
        """
        self.config_path = config_path
        self.frame_size = frame_size
        self.logger = logger or setup_logger("zone_manager")

        self.zones: Dict[str, ZoneDefinition] = {}
        self.entry_regions: Dict[str, ZoneDefinition] = {}
        self.exit_regions: Dict[str, ZoneDefinition] = {}

        self._load_config()
        if self.frame_size:
            self.scale_to_frame_size(self.frame_size[0], self.frame_size[1])

    @property
    def is_normalized(self) -> bool:
        """Return whether loaded zones use normalized (0.0 - 1.0) coordinates."""
        return any(z.is_normalized for z in self.zones.values())

    def scale_to_frame_size(self, width: int, height: int) -> None:
        """
        Scale all normalized zone, entry, and exit polygons to the specified video frame dimensions.
        """
        self.frame_size = (width, height)
        for zone in self.zones.values():
            zone.scale_to_frame(width, height)
        for entry in self.entry_regions.values():
            entry.scale_to_frame(width, height)
        for exit_r in self.exit_regions.values():
            exit_r.scale_to_frame(width, height)
        self.logger.info(f"Scaled zones to frame resolution: {width}x{height}")

    def _load_config(self) -> None:
        """Load and validate zone configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Zone configuration file not found: {self.config_path}\n"
                f"Create a zones.json file or update ZONE_CONFIG_PATH in .env."
            )

        self.logger.info(f"Loading zone configuration from: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in zone configuration: {self.config_path}\n"
                f"Error: {exc}"
            ) from exc

        # Load zones
        raw_zones = config_data.get("zones", [])
        for zone_data in raw_zones:
            zone_def = self._parse_region(zone_data, "zone")
            self.zones[zone_def.id] = zone_def

        # Load entry regions
        raw_entries = config_data.get("entry_regions", [])
        for entry_data in raw_entries:
            entry_def = self._parse_region(entry_data, "entry_region")
            self.entry_regions[entry_def.id] = entry_def

        # Load exit regions
        raw_exits = config_data.get("exit_regions", [])
        for exit_data in raw_exits:
            exit_def = self._parse_region(exit_data, "exit_region")
            self.exit_regions[exit_def.id] = exit_def

        self.logger.info(
            f"Zones loaded: {len(self.zones)} | "
            f"Entry regions: {len(self.entry_regions)} | "
            f"Exit regions: {len(self.exit_regions)}"
        )

        # Check for overlapping zones (warning only)
        self._check_overlapping_zones()

    def _parse_region(self, data: dict, region_type: str) -> ZoneDefinition:
        """
        Parse and validate a single region definition.

        Parameters
        ----------
        data : dict
            Raw JSON region data with 'id', 'name', 'polygon' keys.
        region_type : str
            Type label for error messages ('zone', 'entry_region', 'exit_region').

        Returns
        -------
        ZoneDefinition
            Validated zone definition.

        Raises
        ------
        ValueError
            If required fields are missing or polygon is invalid.
        """
        region_id = data.get("id")
        region_name = data.get("name")
        raw_polygon = data.get("polygon")

        if not region_id:
            raise ValueError(
                f"Missing 'id' field in {region_type} definition: {data}"
            )
        if not region_name:
            raise ValueError(
                f"Missing 'name' field in {region_type} '{region_id}'"
            )
        if not raw_polygon:
            raise ValueError(
                f"Missing 'polygon' field in {region_type} '{region_id}'"
            )

        # Validate polygon geometry
        self._validate_polygon(raw_polygon, region_id, region_type)

        raw_points = [(float(p[0]), float(p[1])) for p in raw_polygon]
        # Check if coordinates are normalized (all coordinates <= 1.0 and any float < 1.0)
        is_normalized = all(0.0 <= p[0] <= 1.0 and 0.0 <= p[1] <= 1.0 for p in raw_points) and any(
            isinstance(p[0], float) or isinstance(p[1], float) for p in raw_points
        )

        if is_normalized and self.frame_size:
            w, h = self.frame_size
            polygon = [(int(round(p[0] * w)), int(round(p[1] * h))) for p in raw_points]
        else:
            polygon = [(int(round(p[0])), int(round(p[1]))) for p in raw_points]

        return ZoneDefinition(
            id=region_id,
            name=region_name,
            polygon=polygon,
            raw_polygon=raw_points,
            is_normalized=is_normalized,
        )

    def _validate_polygon(
        self, polygon: list, region_id: str, region_type: str
    ) -> None:
        """
        Validate polygon geometry.

        Parameters
        ----------
        polygon : list
            List of [x, y] coordinate pairs.
        region_id : str
            Region identifier for error messages.
        region_type : str
            Region type for error messages.

        Raises
        ------
        ValueError
            If polygon has fewer than 3 vertices or contains invalid coordinates.
        """
        if len(polygon) < 3:
            raise ValueError(
                f"Invalid polygon for {region_type} '{region_id}': "
                f"requires at least 3 vertices, got {len(polygon)}."
            )

        for i, point in enumerate(polygon):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(
                    f"Invalid vertex {i} in {region_type} '{region_id}': "
                    f"expected [x, y], got {point}"
                )
            try:
                float(point[0])
                float(point[1])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Non-numeric coordinate at vertex {i} in {region_type} "
                    f"'{region_id}': {point}"
                ) from exc

    def _check_overlapping_zones(self) -> None:
        """Log warnings for potentially overlapping zone polygons."""
        zone_list = list(self.zones.values())
        for i in range(len(zone_list)):
            for j in range(i + 1, len(zone_list)):
                zone_a = zone_list[i]
                zone_b = zone_list[j]

                # Check if any vertex of zone_a is inside zone_b
                for px, py in zone_a.polygon:
                    result = cv2.pointPolygonTest(
                        zone_b.contour, (float(px), float(py)), False
                    )
                    if result >= 0:
                        self.logger.warning(
                            f"Potential overlap detected between "
                            f"zone '{zone_a.id}' ({zone_a.name}) and "
                            f"zone '{zone_b.id}' ({zone_b.name})"
                        )
                        break

    def point_in_polygon(
        self, x: int, y: int, zone_def: ZoneDefinition
    ) -> bool:
        """
        Test whether a point is inside a zone polygon.

        Uses cv2.pointPolygonTest for accurate polygon containment.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.
        zone_def : ZoneDefinition
            Zone definition with pre-computed contour.

        Returns
        -------
        bool
            True if the point is inside or on the boundary of the polygon.
        """
        result = cv2.pointPolygonTest(zone_def.contour, (float(x), float(y)), False)
        return result >= 0

    def point_in_zone(
        self, x: int, y: int, zone: str | ZoneDefinition
    ) -> bool:
        """
        Test whether a point is inside a specific zone by ID or definition.
        """
        if isinstance(zone, str):
            zone_def = self.zones.get(zone)
            if not zone_def:
                return False
        else:
            zone_def = zone
        return self.point_in_polygon(x, y, zone_def)

    def get_zones_for_point(self, x: int, y: int) -> List[str]:
        """
        Find all zones that contain the given point.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.

        Returns
        -------
        List[str]
            List of zone IDs containing the point.
        """
        containing_zones = []
        for zone_id, zone_def in self.zones.items():
            if self.point_in_polygon(x, y, zone_def):
                containing_zones.append(zone_id)
        return containing_zones

    def get_zone_name(self, zone_id: str) -> str:
        """
        Get the display name for a zone ID.

        Parameters
        ----------
        zone_id : str
            Zone identifier.

        Returns
        -------
        str
            Zone name, or the zone_id if not found.
        """
        zone_def = self.zones.get(zone_id)
        return zone_def.name if zone_def else zone_id

    def is_in_entry_region(self, x: int, y: int) -> Optional[str]:
        """
        Check if a point is inside any entry region.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.

        Returns
        -------
        Optional[str]
            Entry region ID if inside one, else None.
        """
        for region_id, region_def in self.entry_regions.items():
            if self.point_in_polygon(x, y, region_def):
                return region_id
        return None

    def is_in_exit_region(self, x: int, y: int) -> Optional[str]:
        """
        Check if a point is inside any exit region.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.

        Returns
        -------
        Optional[str]
            Exit region ID if inside one, else None.
        """
        for region_id, region_def in self.exit_regions.items():
            if self.point_in_polygon(x, y, region_def):
                return region_id
        return None

    def get_all_zone_ids(self) -> List[str]:
        """Return a list of all zone IDs."""
        return list(self.zones.keys())

    def get_all_zones(self) -> List[ZoneDefinition]:
        """Return all zone definitions."""
        return list(self.zones.values())

    def get_all_entry_regions(self) -> List[ZoneDefinition]:
        """Return all entry region definitions."""
        return list(self.entry_regions.values())

    def get_all_exit_regions(self) -> List[ZoneDefinition]:
        """Return all exit region definitions."""
        return list(self.exit_regions.values())
