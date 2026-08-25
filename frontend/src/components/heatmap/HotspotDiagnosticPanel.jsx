/**
 * HotspotDiagnosticPanel
 * =======================
 * Displays categorized retail hotspots, conversion zones, dead zones,
 * and actionable merchandising recommendations.
 */

import { useMemo } from "react";

const ZONE_STYLE = {
  HOTSPOT: {
    icon: "🔥",
    color: "#f87171",
    bg: "rgba(248, 113, 113, 0.1)",
    border: "rgba(248, 113, 113, 0.25)",
    label: "Hotspot",
  },
  CONVERSION_ZONE: {
    icon: "💰",
    color: "#4ade80",
    bg: "rgba(74, 222, 128, 0.1)",
    border: "rgba(74, 222, 128, 0.25)",
    label: "Conversion Zone",
  },
  TRANSIT_CORRIDOR: {
    icon: "🚶",
    color: "#60a5fa",
    bg: "rgba(96, 165, 250, 0.1)",
    border: "rgba(96, 165, 250, 0.25)",
    label: "Transit Corridor",
  },
  DEAD_ZONE: {
    icon: "⚠️",
    color: "#94a3b8",
    bg: "rgba(148, 163, 184, 0.1)",
    border: "rgba(148, 163, 184, 0.25)",
    label: "Dead Zone",
  },
};

const SEVERITY_COLORS = {
  LOW: "#4ade80",
  MEDIUM: "#fbbf24",
  HIGH: "#f87171",
};

export default function HotspotDiagnosticPanel({
  diagnostics, // from API: { zones, summary, grid_cols, grid_rows }
  className = "",
}) {
  const zones = diagnostics?.zones || [];
  const summary = diagnostics?.summary || {};

  const groupedZones = useMemo(() => {
    const groups = {};
    for (const zone of zones) {
      const type = zone.zone_type;
      if (!groups[type]) groups[type] = [];
      groups[type].push(zone);
    }
    return groups;
  }, [zones]);

  if (zones.length === 0) {
    return (
      <div className={`bg-gray-900/60 border border-gray-800/60 rounded-xl p-6 text-center ${className}`}>
        <p className="text-gray-500 text-sm">No diagnostic zones detected</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ── Summary Cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { type: "HOTSPOT", count: summary.hotspot_count },
          { type: "CONVERSION_ZONE", count: summary.conversion_zone_count },
          { type: "TRANSIT_CORRIDOR", count: summary.transit_corridor_count },
          { type: "DEAD_ZONE", count: summary.dead_zone_count },
        ].map(({ type, count }) => {
          const style = ZONE_STYLE[type];
          return (
            <div
              key={type}
              className="rounded-xl border p-3 text-center"
              style={{
                backgroundColor: style.bg,
                borderColor: style.border,
              }}
            >
              <span className="text-2xl">{style.icon}</span>
              <p
                className="text-xl font-bold tabular-nums mt-1"
                style={{ color: style.color }}
              >
                {count || 0}
              </p>
              <p className="text-[10px] text-gray-400 mt-0.5">{style.label}</p>
            </div>
          );
        })}
      </div>

      {/* ── DTR KPI ──────────────────────────────────────────── */}
      <div className="bg-gray-900/60 border border-gray-800/60 rounded-xl p-4 flex items-center justify-between">
        <div>
          <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
            Avg Dwell-to-Transit Ratio
          </span>
          <p className="text-xs text-gray-500 mt-0.5">
            Higher = more visual engagement relative to passing traffic
          </p>
        </div>
        <span
          className="text-2xl font-bold tabular-nums"
          style={{
            color: (summary.avg_dwell_to_transit_ratio || 0) > 1.0 ? "#4ade80" :
                   (summary.avg_dwell_to_transit_ratio || 0) > 0.5 ? "#fbbf24" : "#f87171",
          }}
        >
          {(summary.avg_dwell_to_transit_ratio || 0).toFixed(2)}
        </span>
      </div>

      {/* ── Zone Detail Cards ────────────────────────────────── */}
      <div className="space-y-3">
        {Object.entries(groupedZones).map(([type, items]) => {
          const style = ZONE_STYLE[type] || ZONE_STYLE.DEAD_ZONE;
          return (
            <div key={type} className="space-y-2">
              <h4
                className="text-xs font-semibold uppercase tracking-wider flex items-center gap-2"
                style={{ color: style.color }}
              >
                <span>{style.icon}</span>
                {style.label}s ({items.length})
              </h4>
              {items.map((zone, idx) => (
                <div
                  key={`${type}-${idx}`}
                  className="rounded-xl border p-3 space-y-2"
                  style={{
                    backgroundColor: style.bg,
                    borderColor: style.border,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-gray-300">
                      Grid [{zone.row}, {zone.col}]
                    </span>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                      style={{
                        color: SEVERITY_COLORS[zone.severity] || "#94a3b8",
                        backgroundColor: `${SEVERITY_COLORS[zone.severity] || "#94a3b8"}22`,
                      }}
                    >
                      {zone.severity}
                    </span>
                  </div>
                  {/* Metrics */}
                  <div className="flex items-center gap-4 text-[10px] text-gray-400">
                    <span>
                      <span className="text-gray-500">Attention:</span>{" "}
                      <span className="font-mono text-gray-300">{zone.attention_weight?.toFixed(1)}</span>
                    </span>
                    <span>
                      <span className="text-gray-500">Traffic:</span>{" "}
                      <span className="font-mono text-gray-300">{zone.traffic_weight?.toFixed(1)}</span>
                    </span>
                    <span>
                      <span className="text-gray-500">DTR:</span>{" "}
                      <span className="font-mono text-gray-300">
                        {zone.dwell_to_transit_ratio?.toFixed(2)}
                      </span>
                    </span>
                  </div>
                  {/* Recommendation */}
                  {zone.recommendation && (
                    <p className="text-[11px] text-gray-400 italic border-t border-gray-800/40 pt-2 mt-1">
                      💡 {zone.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
