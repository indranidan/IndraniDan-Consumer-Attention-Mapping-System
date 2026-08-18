"""
Attention Report — Analytics Aggregator
==========================================
Computes all report sections from loaded Phase 3/4/5 data.
This module performs NO video processing or model inference.
It operates exclusively on structured JSON data.
"""

import logging
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from ai.attention_report.data_loader import ReportData
from ai.logger import setup_logger


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Division with zero safety — returns None on division by zero."""
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _safe_round(value: Optional[float], decimals: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, decimals)


class ReportAggregator:
    """Computes all report analytics from loaded data."""

    def __init__(self, data: ReportData, logger: Optional[logging.Logger] = None):
        self.data = data
        self.logger = logger or setup_logger("report_aggregator")

    # ── 6.3 Executive Summary ────────────────────────────────────

    def compute_executive_summary(self) -> Dict[str, Any]:
        ts = self.data.traffic_summary
        sessions = self.data.sessions
        dwell_events = self.data.dwell_events
        attn_events = self.data.attention_events
        zone_dwell = self.data.zone_dwell_summary
        target_summ = self.data.target_attention_summary

        total_shoppers = ts.get("total_unique_shoppers", len(sessions))
        total_sessions = len(sessions)
        completed = sum(1 for s in sessions if s.get("status") == "completed")
        track_lost = sum(1 for s in sessions if s.get("status") == "track_lost")
        total_entries = ts.get("total_entries", 0)
        total_exits = ts.get("total_exits", 0)

        durations = []
        for s in sessions:
            st, et = s.get("start_time"), s.get("end_time")
            if st is not None and et is not None:
                durations.append(et - st)
        avg_session_dur = _safe_div(sum(durations), len(durations)) if durations else 0.0

        total_zone_visits = len(self.data.zone_visits)
        all_dwell = [e.get("dwell_seconds", 0) for e in dwell_events
                     if e.get("dwell_seconds") is not None]
        avg_zone_dwell = _safe_div(sum(all_dwell), len(all_dwell)) if all_dwell else 0.0

        total_attn_events = len(attn_events)
        attn_durs = [e.get("duration_seconds", 0) for e in attn_events
                     if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0]
        total_attn_dur = sum(attn_durs)
        avg_attn_dur = _safe_div(total_attn_dur, len(attn_durs)) if attn_durs else 0.0
        num_targets = len(target_summ)

        # Most visited zone
        zone_stats = ts.get("zone_statistics", [])
        most_visited = max(zone_stats, key=lambda z: z.get("total_visits", 0)) if zone_stats else None

        # Zone with highest average dwell
        highest_avg_dwell = max(zone_dwell, key=lambda z: z.get("average_dwell_seconds", 0)) if zone_dwell else None

        # Most attended target
        most_attended = max(target_summ, key=lambda t: t.get("total_attention_sec", 0)) if target_summ else None

        return {
            "total_unique_shoppers": total_shoppers,
            "total_sessions": total_sessions,
            "completed_sessions": completed,
            "track_lost_sessions": track_lost,
            "total_entries": total_entries,
            "total_exits": total_exits,
            "average_session_duration_sec": _safe_round(avg_session_dur),
            "total_zone_visits": total_zone_visits,
            "average_zone_dwell_time_sec": _safe_round(avg_zone_dwell),
            "total_attention_events": total_attn_events,
            "total_estimated_attention_duration_sec": _safe_round(total_attn_dur),
            "average_estimated_attention_duration_sec": _safe_round(avg_attn_dur),
            "number_of_attention_targets": num_targets,
            "most_visited_zone": {
                "zone_id": most_visited.get("zone_id"),
                "zone_name": most_visited.get("zone_name"),
                "total_visits": most_visited.get("total_visits"),
            } if most_visited else None,
            "zone_with_highest_average_dwell": {
                "zone_id": highest_avg_dwell.get("zone_id"),
                "zone_name": highest_avg_dwell.get("zone_name"),
                "average_dwell_seconds": highest_avg_dwell.get("average_dwell_seconds"),
            } if highest_avg_dwell else None,
            "most_attended_target": {
                "target_id": most_attended.get("target_id"),
                "target_name": most_attended.get("target_name"),
                "total_attention_sec": most_attended.get("total_attention_sec"),
            } if most_attended else None,
        }

    # ── 6.4 Shopper Report ───────────────────────────────────────

    def compute_shopper_reports(self) -> List[Dict[str, Any]]:
        session_map = {s.get("tracking_id"): s for s in self.data.sessions}
        dwell_map = {s.get("tracking_id"): s for s in self.data.shopper_dwell_summary}
        attn_map = {s.get("tracking_id"): s for s in self.data.shopper_attention_summary}

        all_ids = sorted(set(
            list(session_map.keys()) +
            list(dwell_map.keys()) +
            list(attn_map.keys())
        ))

        shoppers = []
        for tid in all_ids:
            sess = session_map.get(tid, {})
            dwell = dwell_map.get(tid, {})
            attn = attn_map.get(tid, {})

            st = sess.get("start_time")
            et = sess.get("end_time")
            duration = (et - st) if st is not None and et is not None else dwell.get("session_duration")

            # Attention event details from attention_events
            shopper_attn_events = [e for e in self.data.attention_events
                                   if e.get("tracking_id") == tid]
            attn_durs = [e.get("duration_seconds", 0) for e in shopper_attn_events
                         if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0]
            longest_attn = max(attn_durs) if attn_durs else 0.0

            # Low-confidence count
            low_conf_count = 0
            total_obs = attn.get("total_observations", 0)
            unknown_obs = attn.get("unknown_observation_count", 0)

            shoppers.append({
                "tracking_id": tid,
                "session_id": sess.get("session_id", f"session_{tid:03d}"),
                "session_status": sess.get("status", dwell.get("session_status", "unknown")),
                "session_duration_sec": _safe_round(duration),
                "entry_time": sess.get("entry_time"),
                "exit_time": sess.get("exit_time"),
                "zones_visited": sess.get("zones_visited", []),
                "number_of_zone_visits": dwell.get("total_zone_visits", 0),
                "total_zone_dwell_time_sec": _safe_round(dwell.get("total_observed_dwell_seconds", 0)),
                "average_zone_dwell_time_sec": _safe_round(dwell.get("average_zone_dwell_seconds", 0)),
                "longest_zone_dwell_sec": _safe_round(dwell.get("longest_zone_visit_seconds", 0)),
                "attention_event_count": attn.get("attention_event_count", 0),
                "total_estimated_attention_duration_sec": _safe_round(attn.get("total_estimated_attention_sec", 0)),
                "average_attention_duration_sec": _safe_round(attn.get("average_attention_sec", 0)),
                "longest_attention_event_sec": _safe_round(longest_attn),
                "most_attended_target": attn.get("most_attended_target", "—"),
                "unknown_attention_observations": unknown_obs,
                "low_confidence_attention_observations": low_conf_count,
            })
        return shoppers

    # ── 6.5 Zone Report ──────────────────────────────────────────

    def compute_zone_reports(self) -> List[Dict[str, Any]]:
        zones = []
        for zd in self.data.zone_dwell_summary:
            zone_id = zd.get("zone_id")
            zone_name = zd.get("zone_name")

            # Attention events in this zone
            zone_attn = [e for e in self.data.attention_events
                         if e.get("zone_id") == zone_id]
            attn_durs = [e.get("duration_seconds", 0) for e in zone_attn
                         if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0]
            total_attn = sum(attn_durs)
            avg_attn = _safe_div(total_attn, len(attn_durs))
            unique_attn_shoppers = len(set(e.get("tracking_id") for e in zone_attn))

            zones.append({
                "zone_id": zone_id,
                "zone_name": zone_name,
                "unique_visitors": zd.get("unique_shoppers", 0),
                "total_visits": zd.get("total_visits", 0),
                "total_dwell_time_sec": _safe_round(zd.get("total_dwell_seconds", 0)),
                "average_dwell_time_sec": _safe_round(zd.get("average_dwell_seconds", 0)),
                "median_dwell_time_sec": _safe_round(zd.get("median_dwell_seconds", 0)),
                "maximum_dwell_time_sec": _safe_round(zd.get("max_dwell_seconds", 0)),
                "attention_event_count": len(zone_attn),
                "total_estimated_attention_duration_sec": _safe_round(total_attn),
                "average_estimated_attention_duration_sec": _safe_round(avg_attn),
                "unique_shoppers_with_attention_events": unique_attn_shoppers,
            })
        return zones

    # ── 6.6 Attention Target Report ──────────────────────────────

    def compute_target_reports(self) -> List[Dict[str, Any]]:
        targets = []
        for t in self.data.target_attention_summary:
            tid = t.get("target_id")
            # Repeated attention: events where same shopper visits same target multiple times
            target_events = [e for e in self.data.attention_events
                             if e.get("target_id") == tid]
            shopper_counts = defaultdict(int)
            for e in target_events:
                shopper_counts[e.get("tracking_id")] += 1
            repeat_count = sum(c - 1 for c in shopper_counts.values() if c > 1)

            targets.append({
                "target_id": tid,
                "target_name": t.get("target_name"),
                "target_type": t.get("target_type", "unknown"),
                "unique_shoppers": t.get("unique_shoppers", 0),
                "attention_event_count": t.get("attention_event_count", 0),
                "total_estimated_attention_duration_sec": _safe_round(t.get("total_attention_sec", 0)),
                "average_attention_duration_sec": _safe_round(t.get("average_attention_sec", 0)),
                "maximum_attention_duration_sec": _safe_round(t.get("maximum_attention_sec", 0)),
                "repeat_attention_count": repeat_count,
            })
        return targets

    # ── 6.7 Attention Direction ──────────────────────────────────

    def compute_attention_direction(self) -> Dict[str, Any]:
        direction_counts: Dict[str, int] = defaultdict(int)
        direction_events: Dict[str, int] = defaultdict(int)

        for e in self.data.attention_events:
            d = e.get("attention_direction", "UNKNOWN")
            direction_counts[d] += 1
            if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0:
                direction_events[d] += 1

        # Also count from shopper observations
        total_obs = sum(s.get("total_observations", 0) for s in self.data.shopper_attention_summary)
        unknown_obs = sum(s.get("unknown_observation_count", 0) for s in self.data.shopper_attention_summary)

        if not direction_counts and total_obs > 0:
            direction_counts["UNKNOWN"] = unknown_obs

        total = sum(direction_counts.values()) if direction_counts else total_obs
        if total == 0:
            total = 1  # Avoid division by zero

        directions = {}
        for d in ["LEFT", "RIGHT", "CENTER", "UP", "DOWN", "UNKNOWN"]:
            count = direction_counts.get(d, 0)
            directions[d] = {
                "observation_count": count,
                "percentage": _safe_round(_safe_div(count * 100, total)),
                "stable_attention_event_count": direction_events.get(d, 0),
            }

        # Add unknown observations from shopper summaries if no events
        if not self.data.attention_events and unknown_obs > 0:
            directions["UNKNOWN"]["observation_count"] = unknown_obs
            directions["UNKNOWN"]["percentage"] = _safe_round(_safe_div(unknown_obs * 100, total_obs))

        return {
            "note": "ESTIMATED ATTENTION DIRECTION — based on head orientation, not exact eye tracking.",
            "total_observations": total_obs if total_obs > 0 else sum(direction_counts.values()),
            "directions": directions,
        }

    # ── 6.8 Attention Confidence ─────────────────────────────────

    def compute_attention_confidence(self) -> Dict[str, Any]:
        confidences = [e.get("confidence", 0) for e in self.data.attention_events
                       if e.get("confidence") is not None]

        total_obs = sum(s.get("total_observations", 0) for s in self.data.shopper_attention_summary)
        unknown_obs = sum(s.get("unknown_observation_count", 0) for s in self.data.shopper_attention_summary)
        known_obs = total_obs - unknown_obs

        if confidences:
            avg_conf = statistics.mean(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            high_conf = sum(1 for c in confidences if c >= 0.6)
            low_conf = sum(1 for c in confidences if c < 0.6)
        else:
            avg_conf = None
            min_conf = None
            max_conf = None
            high_conf = 0
            low_conf = 0

        total_for_pct = total_obs if total_obs > 0 else 1
        return {
            "average_confidence": _safe_round(avg_conf, 4),
            "minimum_confidence": _safe_round(min_conf, 4),
            "maximum_confidence": _safe_round(max_conf, 4),
            "high_confidence_observations": high_conf,
            "low_confidence_observations": low_conf,
            "unknown_observations": unknown_obs,
            "total_observations": total_obs,
            "high_confidence_percentage": _safe_round(_safe_div(high_conf * 100, total_for_pct)),
            "low_confidence_percentage": _safe_round(_safe_div(low_conf * 100, total_for_pct)),
            "unknown_percentage": _safe_round(_safe_div(unknown_obs * 100, total_for_pct)),
        }

    # ── 6.9 Dwell vs Attention ───────────────────────────────────

    def compute_dwell_vs_attention(self) -> Dict[str, Any]:
        comparisons = []
        for zd in self.data.zone_dwell_summary:
            zone_id = zd.get("zone_id")
            zone_name = zd.get("zone_name")
            total_dwell = zd.get("total_dwell_seconds", 0)
            avg_dwell = zd.get("average_dwell_seconds", 0)

            zone_attn = [e for e in self.data.attention_events
                         if e.get("zone_id") == zone_id]
            attn_durs = [e.get("duration_seconds", 0) for e in zone_attn
                         if e.get("duration_seconds") is not None and e.get("duration_seconds", 0) > 0]
            total_attn = sum(attn_durs)
            avg_attn = _safe_div(total_attn, len(attn_durs)) if attn_durs else 0.0

            ratio = _safe_div(total_attn, total_dwell)

            comparisons.append({
                "zone_id": zone_id,
                "zone_name": zone_name,
                "average_dwell_time_sec": _safe_round(avg_dwell),
                "average_estimated_attention_time_sec": _safe_round(avg_attn),
                "total_dwell_time_sec": _safe_round(total_dwell),
                "total_estimated_attention_time_sec": _safe_round(total_attn),
                "attention_to_dwell_ratio": _safe_round(ratio, 4),
            })

        return {
            "note": "This ratio is purely descriptive. It does NOT indicate purchase intent, "
                    "customer interest score, conversion probability, or product preference.",
            "zones": comparisons,
        }

    # ── 6.10 Repeated Attention ──────────────────────────────────

    def compute_repeated_attention(self) -> Dict[str, Any]:
        shopper_target_events: Dict[Tuple[int, str], List[Dict]] = defaultdict(list)
        for e in self.data.attention_events:
            key = (e.get("tracking_id"), e.get("target_id"))
            shopper_target_events[key].append(e)

        repeated = []
        for (tid, target_id), events in shopper_target_events.items():
            if len(events) > 1:
                repeated.append({
                    "tracking_id": tid,
                    "target_id": target_id,
                    "target_name": events[0].get("target_name", "Unknown"),
                    "repeat_count": len(events),
                    "events": [
                        {
                            "event_number": i + 1,
                            "duration_seconds": _safe_round(e.get("duration_seconds")),
                        }
                        for i, e in enumerate(events)
                    ],
                })

        unique_shoppers = len(set(r["tracking_id"] for r in repeated))
        total_repeat_count = sum(r["repeat_count"] - 1 for r in repeated)

        # Most repeatedly attended target
        target_repeat: Dict[str, int] = defaultdict(int)
        for r in repeated:
            target_repeat[r["target_name"]] += r["repeat_count"]
        most_repeated = max(target_repeat, key=target_repeat.get) if target_repeat else None

        return {
            "total_repeat_attention_count": total_repeat_count,
            "unique_shoppers_with_repeated_attention": unique_shoppers,
            "most_repeatedly_attended_target": most_repeated,
            "repeated_events": repeated,
        }

    # ── 6.11 Rankings ────────────────────────────────────────────

    def compute_rankings(self) -> Dict[str, Any]:
        zone_reports = self.compute_zone_reports()
        target_reports = self.compute_target_reports()

        def _top(items, key, n=10):
            return sorted(items, key=lambda x: x.get(key, 0), reverse=True)[:n]

        top_zones = {
            "by_unique_visitors": _top(zone_reports, "unique_visitors"),
            "by_total_visits": _top(zone_reports, "total_visits"),
            "by_total_dwell_time": _top(zone_reports, "total_dwell_time_sec"),
            "by_average_dwell_time": _top(zone_reports, "average_dwell_time_sec"),
            "by_attention_event_count": _top(zone_reports, "attention_event_count"),
            "by_estimated_attention_duration": _top(zone_reports, "total_estimated_attention_duration_sec"),
        }

        top_targets = {
            "by_unique_shoppers": _top(target_reports, "unique_shoppers"),
            "by_attention_event_count": _top(target_reports, "attention_event_count"),
            "by_total_attention_duration": _top(target_reports, "total_estimated_attention_duration_sec"),
            "by_average_attention_duration": _top(target_reports, "average_attention_duration_sec"),
            "by_repeat_attention_count": _top(target_reports, "repeat_attention_count"),
        }

        return {"top_zones": top_zones, "top_targets": top_targets}

    # ── 6.12 Time-Based Analytics ────────────────────────────────

    def compute_time_series(self) -> Dict[str, Any]:
        traffic_by_time = self.data.traffic_summary.get("traffic_by_time_period", [])

        # Zone traffic over time
        zone_time: Dict[str, List] = defaultdict(list)
        for zv in self.data.zone_visits:
            zid = zv.get("zone_id", "unknown")
            zone_time[zid].append({
                "entry_time": zv.get("entry_time"),
                "exit_time": zv.get("exit_time"),
                "duration": zv.get("duration"),
            })

        # Dwell activity bins
        dwell_time_bins: List[Dict] = []
        for de in self.data.dwell_events:
            entry = de.get("entry_time")
            if entry is not None:
                dwell_time_bins.append({
                    "time": entry,
                    "dwell_seconds": de.get("dwell_seconds", 0),
                    "zone_id": de.get("zone_id"),
                })

        # Attention events over time
        attn_time: List[Dict] = []
        for ae in self.data.attention_events:
            st = ae.get("start_time")
            if st is not None:
                attn_time.append({
                    "time": st,
                    "duration_seconds": ae.get("duration_seconds"),
                    "target_id": ae.get("target_id"),
                })

        return {
            "note": "Timestamps are video-relative. Do not interpret as real-world dates or business hours.",
            "shopper_traffic_over_time": traffic_by_time,
            "zone_traffic_over_time": {zid: events for zid, events in zone_time.items()},
            "dwell_activity_over_time": dwell_time_bins,
            "attention_events_over_time": attn_time,
        }

    # ── 6.13 Data Quality ────────────────────────────────────────

    def compute_data_quality(self) -> Dict[str, Any]:
        sessions = self.data.sessions
        dwell_events = self.data.dwell_events
        attn_summ = self.data.shopper_attention_summary

        total_sessions = len(sessions)
        track_lost = sum(1 for s in sessions if s.get("status") == "track_lost")
        completed = sum(1 for s in sessions if s.get("status") == "completed")

        no_zone = sum(1 for s in sessions if not s.get("zones_visited"))
        missing_entry = sum(1 for s in sessions if s.get("entry_time") is None)
        missing_exit = sum(1 for s in sessions if s.get("exit_time") is None)

        total_obs = sum(s.get("total_observations", 0) for s in attn_summ)
        unknown_obs = sum(s.get("unknown_observation_count", 0) for s in attn_summ)
        known_obs = total_obs - unknown_obs

        incomplete_attn = sum(1 for e in self.data.attention_events
                              if e.get("status") == "track_lost")

        ts = total_sessions if total_sessions > 0 else 1
        to = total_obs if total_obs > 0 else 1

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed,
            "track_lost_sessions": track_lost,
            "track_lost_percentage": _safe_round(_safe_div(track_lost * 100, ts)),
            "sessions_without_zone_assignment": no_zone,
            "missing_zone_percentage": _safe_round(_safe_div(no_zone * 100, ts)),
            "sessions_missing_entry_time": missing_entry,
            "sessions_missing_exit_time": missing_exit,
            "total_attention_observations": total_obs,
            "unknown_attention_observations": unknown_obs,
            "unknown_attention_percentage": _safe_round(_safe_div(unknown_obs * 100, to)),
            "low_confidence_observations": 0,
            "incomplete_attention_events": incomplete_attn,
            "missing_timestamps": missing_entry + missing_exit,
        }

    # ── Aggregate All ────────────────────────────────────────────

    def aggregate_all(self) -> Dict[str, Any]:
        """Compute all report sections and return the full report dict."""
        self.logger.info("Generating executive summary...")
        summary = self.compute_executive_summary()

        self.logger.info("Generating shopper analytics...")
        shoppers = self.compute_shopper_reports()

        self.logger.info("Generating zone analytics...")
        zones = self.compute_zone_reports()

        self.logger.info("Generating attention target analytics...")
        targets = self.compute_target_reports()

        self.logger.info("Generating attention direction analytics...")
        direction = self.compute_attention_direction()

        self.logger.info("Generating attention confidence analytics...")
        confidence = self.compute_attention_confidence()

        self.logger.info("Generating dwell vs attention comparison...")
        dwell_vs_attn = self.compute_dwell_vs_attention()

        self.logger.info("Generating repeated attention analytics...")
        repeated = self.compute_repeated_attention()

        self.logger.info("Generating rankings...")
        rankings = self.compute_rankings()

        self.logger.info("Generating time-based analytics...")
        time_series = self.compute_time_series()

        self.logger.info("Generating data quality metrics...")
        data_quality = self.compute_data_quality()

        return {
            "summary": summary,
            "shoppers": shoppers,
            "zones": zones,
            "targets": targets,
            "attention_direction": direction,
            "confidence": confidence,
            "dwell_vs_attention": dwell_vs_attn,
            "repeated_attention": repeated,
            "rankings": rankings,
            "time_series": time_series,
            "data_quality": data_quality,
        }
