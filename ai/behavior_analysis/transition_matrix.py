"""
Module 6 — Transition Matrix Builder
========================================
Computes zone-to-zone Markov transition probability matrix.
"""

import logging
from typing import Any, Dict, List


logger = logging.getLogger("transition_matrix")


class TransitionMatrixBuilder:
    """Builds a zone-to-zone transition probability matrix from journey data."""

    def build_matrix(
        self,
        journeys: List[Dict[str, Any]],
        zone_names: List[str],
        min_sessions: int = 3,
    ) -> Dict[str, Any]:
        """
        Compute transition probabilities from observed zone sequences.

        Parameters
        ----------
        journeys : list of journey dicts, each with 'timeline' containing stage events.
        zone_names : list of all known zone names.
        min_sessions : minimum sessions for confident statistics.

        Returns
        -------
        dict with 'zones', 'matrix' (list of lists), 'transition_counts',
        'low_confidence', 'total_transitions'.
        """
        # Build count matrix
        zone_index = {z: i for i, z in enumerate(zone_names)}
        n = len(zone_names)
        counts = [[0] * n for _ in range(n)]
        total_transitions = 0

        for journey in journeys:
            # Extract zone sequence from timeline
            zone_sequence = []
            for evt in journey.get("timeline", []):
                zone = evt.get("zone")
                if zone and evt.get("stage") in ("ENTRY", "ZONE_VISIT", "EXIT"):
                    zone_sequence.append(zone)

            # Count transitions
            for i in range(len(zone_sequence) - 1):
                from_zone = zone_sequence[i]
                to_zone = zone_sequence[i + 1]
                if from_zone in zone_index and to_zone in zone_index:
                    counts[zone_index[from_zone]][zone_index[to_zone]] += 1
                    total_transitions += 1

        # Normalize rows to probabilities
        matrix = []
        for row in counts:
            row_sum = sum(row)
            if row_sum > 0:
                matrix.append([round(c / row_sum, 4) for c in row])
            else:
                matrix.append([0.0] * n)

        low_confidence = len(journeys) < min_sessions

        # Also provide human-readable transition list
        transition_list = []
        for i, from_zone in enumerate(zone_names):
            for j, to_zone in enumerate(zone_names):
                if counts[i][j] > 0:
                    transition_list.append({
                        "from_zone": from_zone,
                        "to_zone": to_zone,
                        "count": counts[i][j],
                        "probability": matrix[i][j],
                    })

        return {
            "zones": zone_names,
            "matrix": matrix,
            "transitions": sorted(transition_list, key=lambda x: x["count"], reverse=True),
            "low_confidence": low_confidence,
            "total_transitions": total_transitions,
            "total_sessions": len(journeys),
        }
