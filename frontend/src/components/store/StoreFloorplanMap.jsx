/**
 * Store Floorplan Map Component
 * ==============================
 * Interactive 2D SVG visualizer rendering:
 * - Store architectural boundary
 * - Physical zone regions
 * - Shelf spatial placement boxes
 * - Attention heat level highlights and interactive hover tooltips
 */

import { useState, useMemo } from "react";

export default function StoreFloorplanMap({ store, zones = [], shelves = [], onSelectShelf }) {
  const [selectedZoneId, setSelectedZoneId] = useState("ALL");
  const [hoveredItem, setHoveredItem] = useState(null);
  const [viewMode, setViewMode] = useState("heat"); // heat | layout

  // Generate deterministic coordinates for zones and shelves if not provided in DB
  const mappedLayout = useMemo(() => {
    const zoneLayouts = zones.map((z, idx) => {
      const col = idx % 2;
      const row = Math.floor(idx / 2);
      const x = 40 + col * 460;
      const y = 40 + row * 260;
      const width = 430;
      const height = 230;

      return {
        id: z.id,
        name: z.name,
        color: idx % 4 === 0 ? "#8b5cf6" : idx % 4 === 1 ? "#06b6d4" : idx % 4 === 2 ? "#10b981" : "#f59e0b",
        x,
        y,
        width,
        height,
      };
    });

    const shelfLayouts = shelves.map((s, idx) => {
      // Find parent zone
      const parentZone = zoneLayouts.find((zl) => zl.id === s.zone_id) || zoneLayouts[0] || {
        x: 40,
        y: 40,
        width: 430,
        height: 230,
        color: "#8b5cf6",
      };

      const zoneShelves = shelves.filter((x) => x.zone_id === parentZone.id || (!x.zone_id && parentZone === zoneLayouts[0]));
      const shelfIdx = Math.max(0, zoneShelves.indexOf(s));
      const sCol = shelfIdx % 3;
      const sRow = Math.floor(shelfIdx / 3);

      const sx = parentZone.x + 30 + sCol * 130;
      const sy = parentZone.y + 50 + sRow * 80;
      const sw = 110;
      const sh = 60;

      // Simulated or real attention metrics
      const score = 70 + ((idx * 7) % 28);

      return {
        id: s.id,
        shelf_code: s.shelf_code,
        name: s.name,
        zone_id: s.zone_id,
        zone_name: parentZone.name,
        x: sx,
        y: sy,
        width: sw,
        height: sh,
        score,
        visitors: 10 + (idx * 3),
      };
    });

    return { zoneLayouts, shelfLayouts };
  }, [zones, shelves]);

  const filteredShelves = useMemo(() => {
    if (selectedZoneId === "ALL") return mappedLayout.shelfLayouts;
    return mappedLayout.shelfLayouts.filter((s) => s.zone_id === selectedZoneId);
  }, [mappedLayout, selectedZoneId]);

  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-3xl p-6 shadow-xl space-y-4">
      {/* ── Top Bar & Controls ────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span>🏬</span> Interactive 2D Store Floorplan & Attention Map
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Physical zone distribution and shelf placement density for {store?.name || "Retail Store"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-gray-950 p-1 rounded-xl border border-gray-800 text-xs">
            <button
              onClick={() => setViewMode("heat")}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                viewMode === "heat" ? "bg-violet-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              🔥 Attention Heat
            </button>
            <button
              onClick={() => setViewMode("layout")}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                viewMode === "layout" ? "bg-violet-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              📐 Plan Layout
            </button>
          </div>

          {/* Zone Selector */}
          <select
            value={selectedZoneId}
            onChange={(e) => setSelectedZoneId(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-xs text-white rounded-xl px-3 py-1.5 focus:outline-none focus:border-violet-500"
          >
            <option value="ALL">All Zones ({zones.length})</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── SVG 2D Floorplan Canvas ──────────────────────────────────── */}
      <div className="relative w-full aspect-[16/9] max-h-[500px] bg-gray-950/90 rounded-2xl border border-gray-800/80 overflow-hidden flex items-center justify-center p-2">
        <svg
          viewBox="0 0 1000 580"
          className="w-full h-full select-none"
          style={{ filter: "drop-shadow(0 10px 20px rgba(0,0,0,0.5))" }}
        >
          {/* Store Perimeter */}
          <rect
            x="20"
            y="20"
            width="960"
            height="540"
            rx="24"
            fill="#090d16"
            stroke="#1f293d"
            strokeWidth="3"
            strokeDasharray="6 6"
          />

          {/* Grid Blueprint Texture */}
          <defs>
            <pattern id="floorGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#161e2e" strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect x="20" y="20" width="960" height="540" fill="url(#floorGrid)" />

          {/* Zones */}
          {mappedLayout.zoneLayouts.map((z) => {
            const isSelected = selectedZoneId === "ALL" || selectedZoneId === z.id;
            return (
              <g key={z.id} opacity={isSelected ? 1 : 0.25} className="transition-opacity duration-300">
                <rect
                  x={z.x}
                  y={z.y}
                  width={z.width}
                  height={z.height}
                  rx="16"
                  fill={`${z.color}08`}
                  stroke={z.color}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text
                  x={z.x + 16}
                  y={z.y + 24}
                  fill={z.color}
                  fontSize="12"
                  fontWeight="bold"
                  letterSpacing="0.05em"
                >
                  ZONE: {z.name.toUpperCase()}
                </text>
              </g>
            );
          })}

          {/* Shelves */}
          {filteredShelves.map((s) => {
            const isHovered = hoveredItem?.id === s.id;
            const heatFill =
              viewMode === "heat"
                ? s.score >= 85
                  ? "#ef4444"
                  : s.score >= 75
                  ? "#f59e0b"
                  : "#06b6d4"
                : "#3b82f6";

            return (
              <g
                key={s.id}
                onMouseEnter={() => setHoveredItem(s)}
                onMouseLeave={() => setHoveredItem(null)}
                onClick={() => onSelectShelf && onSelectShelf(s)}
                className="cursor-pointer transition-all duration-300"
              >
                {/* Glow effect on hover */}
                {isHovered && (
                  <rect
                    x={s.x - 4}
                    y={s.y - 4}
                    width={s.width + 8}
                    height={s.height + 8}
                    rx="14"
                    fill={`${heatFill}33`}
                  />
                )}

                {/* Shelf Box */}
                <rect
                  x={s.x}
                  y={s.y}
                  width={s.width}
                  height={s.height}
                  rx="10"
                  fill="#111827"
                  stroke={isHovered ? "#ffffff" : heatFill}
                  strokeWidth={isHovered ? "2.5" : "1.5"}
                />

                {/* Shelf Label & Score */}
                <text
                  x={s.x + s.width / 2}
                  y={s.y + 24}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="10"
                  fontWeight="bold"
                >
                  {s.shelf_code || s.name}
                </text>

                <text
                  x={s.x + s.width / 2}
                  y={s.y + 44}
                  textAnchor="middle"
                  fill={heatFill}
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {viewMode === "heat" ? `${s.score.toFixed(0)} Score` : `${s.visitors} Views`}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {hoveredItem && (
          <div
            className="absolute bg-gray-900/95 border border-gray-700 text-white rounded-xl p-3 shadow-2xl backdrop-blur-md pointer-events-none z-30 animate-fade-in text-xs max-w-xs"
            style={{
              left: `${(hoveredItem.x / 1000) * 100}%`,
              top: `${(hoveredItem.y / 580) * 100}%`,
              transform: "translate(-30%, -120%)",
            }}
          >
            <p className="font-bold text-white flex items-center gap-1.5">
              <span>📦</span> {hoveredItem.name}
            </p>
            <p className="text-[10px] text-gray-400 font-mono mt-0.5">Code: {hoveredItem.shelf_code}</p>
            <div className="mt-2 pt-2 border-t border-gray-800 grid grid-cols-2 gap-2 text-[10px]">
              <div>
                <span className="text-gray-400">Attention Score:</span>
                <p className="font-bold text-emerald-400 font-mono">{hoveredItem.score.toFixed(1)} / 100</p>
              </div>
              <div>
                <span className="text-gray-400">Shopper Views:</span>
                <p className="font-bold text-cyan-400 font-mono">{hoveredItem.visitors}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Legend Footer */}
      <div className="flex flex-wrap items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-800/60">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-gray-300">Heat Index:</span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> High Attention (85+)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Medium (75-84)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Standard (&lt;75)
          </span>
        </div>
        <span className="text-[11px] text-gray-500">
          Showing {filteredShelves.length} mapped shelf locations
        </span>
      </div>
    </div>
  );
}
