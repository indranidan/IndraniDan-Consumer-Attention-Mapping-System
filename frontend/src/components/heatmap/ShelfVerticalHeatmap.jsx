/**
 * ShelfVerticalHeatmap
 * =====================
 * Visualizes shelf planogram tier breakdown with eye-level attention
 * concentration metrics and vertical gaze density bar charts.
 */

import { useMemo } from "react";

const TIER_COLORS = {
  TOP_SHELF: { bg: "rgba(244, 114, 182, 0.15)", bar: "#f472b6", border: "rgba(244, 114, 182, 0.3)" },
  EYE_LEVEL: { bg: "rgba(139, 92, 246, 0.15)", bar: "#a78bfa", border: "rgba(139, 92, 246, 0.3)" },
  REACH_LEVEL: { bg: "rgba(6, 182, 212, 0.15)", bar: "#22d3ee", border: "rgba(6, 182, 212, 0.3)" },
  BOTTOM_SHELF: { bg: "rgba(100, 116, 139, 0.15)", bar: "#94a3b8", border: "rgba(100, 116, 139, 0.3)" },
};

const TIER_ICONS = {
  TOP_SHELF: "🔝",
  EYE_LEVEL: "👁️",
  REACH_LEVEL: "🤚",
  BOTTOM_SHELF: "⬇️",
};

export default function ShelfVerticalHeatmap({
  shelfData,  // from getShelfHeatmap: { shelf_id, shelf_name, vertical_analysis, horizontal_analysis, ... }
  className = "",
}) {
  const vertical = shelfData?.vertical_analysis || {};
  const horizontal = shelfData?.horizontal_analysis || {};
  const tiers = vertical?.vertical_distribution || [];
  const bins = horizontal?.bins || [];
  const eyeConcentration = vertical?.eye_level_concentration || 0;

  const maxTierPct = useMemo(
    () => Math.max(...tiers.map((t) => t.percentage || 0), 1),
    [tiers]
  );
  const maxBinIntensity = useMemo(
    () => Math.max(...bins.map((b) => b.normalized_intensity || 0), 0.01),
    [bins]
  );

  if (!shelfData || tiers.length === 0) {
    return (
      <div className={`bg-gray-900/60 border border-gray-800/60 rounded-xl p-6 text-center ${className}`}>
        <p className="text-gray-500 text-sm">No shelf gaze data available</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-white">
            {shelfData.shelf_name || "Shelf"} — Vertical Gaze Profile
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">
            {vertical.total_gaze_events || 0} gaze events · {(vertical.total_weight || 0).toFixed(1)}s total
          </p>
        </div>
        {/* Eye-Level KPI */}
        <div className="flex flex-col items-end">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Eye-Level Focus</span>
          <span
            className="text-xl font-bold tabular-nums"
            style={{ color: eyeConcentration >= 40 ? "#a78bfa" : eyeConcentration >= 20 ? "#fbbf24" : "#f87171" }}
          >
            {eyeConcentration.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* ── Vertical Tier Bars ──────────────────────────────── */}
      <div className="bg-gray-900/60 border border-gray-800/60 rounded-xl p-4 space-y-3">
        {tiers.map((tier) => {
          const colors = TIER_COLORS[tier.tier] || TIER_COLORS.BOTTOM_SHELF;
          const icon = TIER_ICONS[tier.tier] || "📍";
          const barWidth = (tier.percentage / maxTierPct) * 100;

          return (
            <div key={tier.tier} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{icon}</span>
                  <span className="text-xs font-semibold text-gray-300">{tier.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-gray-400">
                    {tier.gaze_events} events
                  </span>
                  <span
                    className="text-xs font-bold tabular-nums"
                    style={{ color: colors.bar }}
                  >
                    {tier.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              {/* Bar */}
              <div className="h-3 bg-gray-800/80 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${barWidth}%`,
                    background: `linear-gradient(90deg, ${colors.bar}cc, ${colors.bar}50)`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Horizontal Distribution ──────────────────────────── */}
      {bins.length > 0 && (
        <div className="bg-gray-900/60 border border-gray-800/60 rounded-xl p-4">
          <h5 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Horizontal Planogram Spread
          </h5>
          <div className="flex items-end gap-[2px] h-16">
            {bins.map((bin) => {
              const barH = (bin.normalized_intensity / maxBinIntensity) * 100;
              return (
                <div
                  key={bin.bin_index}
                  className="flex-1 rounded-t transition-all duration-500 group relative"
                  style={{
                    height: `${Math.max(barH, 2)}%`,
                    background: `linear-gradient(180deg, rgba(139, 92, 246, ${0.3 + bin.normalized_intensity * 0.6}), rgba(139, 92, 246, 0.1))`,
                  }}
                >
                  {/* Tooltip */}
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 hidden group-hover:block bg-gray-800 text-[10px] text-gray-300 rounded px-2 py-1 whitespace-nowrap z-10">
                    Bin {bin.bin_index + 1}: {bin.percentage.toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-gray-500">Left</span>
            <span className="text-[9px] text-gray-500">Right</span>
          </div>
        </div>
      )}
    </div>
  );
}
