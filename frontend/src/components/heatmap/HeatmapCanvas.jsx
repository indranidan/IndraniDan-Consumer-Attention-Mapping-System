/**
 * HeatmapCanvas
 * ==============
 * Interactive HTML5 Canvas multi-layer heatmap renderer.
 * Supports:
 * - Gaze attention, traffic, interaction, and hotspot layers
 * - Custom colormap selection (JET, TURBO, INFERNO, VIRIDIS)
 * - Opacity slider and intensity threshold controls
 */

import { useState, useRef, useEffect, useCallback } from "react";

// ── Colormap Gradient Definitions ────────────────────────────
const COLORMAPS = {
  JET: [
    [0, 0, 131], [0, 60, 170], [0, 120, 220], [0, 180, 255],
    [0, 235, 200], [50, 255, 150], [130, 255, 80], [210, 255, 0],
    [255, 200, 0], [255, 130, 0], [255, 60, 0], [200, 0, 0], [128, 0, 0],
  ],
  TURBO: [
    [48, 18, 59], [70, 60, 150], [60, 120, 210], [30, 180, 220],
    [30, 220, 170], [80, 240, 100], [160, 240, 50], [220, 220, 30],
    [255, 180, 20], [255, 120, 20], [240, 60, 30], [190, 20, 30], [122, 4, 3],
  ],
  INFERNO: [
    [0, 0, 4], [20, 11, 53], [58, 9, 99], [96, 19, 110],
    [133, 33, 107], [169, 55, 87], [203, 80, 60], [231, 116, 36],
    [248, 157, 14], [252, 200, 40], [245, 244, 115],
  ],
  VIRIDIS: [
    [68, 1, 84], [72, 36, 117], [65, 68, 135], [53, 95, 141],
    [42, 120, 142], [33, 145, 140], [34, 168, 132], [53, 191, 115],
    [94, 211, 85], [155, 227, 45], [229, 240, 30],
  ],
};

function interpolateColor(stops, t) {
  const n = stops.length - 1;
  const i = Math.min(Math.floor(t * n), n - 1);
  const frac = t * n - i;
  const c1 = stops[i];
  const c2 = stops[i + 1];
  return [
    Math.round(c1[0] + (c2[0] - c1[0]) * frac),
    Math.round(c1[1] + (c2[1] - c1[1]) * frac),
    Math.round(c1[2] + (c2[2] - c1[2]) * frac),
  ];
}

export default function HeatmapCanvas({
  gridData,       // { grid_width, grid_height, cells: [{x, y, intensity}] }
  flowVectors,    // [{x, y, dx, dy, speed}]
  hotspotZones,   // [{center_x, center_y, zone_type, ...}]
  width = 800,
  height = 500,
  className = "",
}) {
  const canvasRef = useRef(null);
  const [colormap, setColormap] = useState("JET");
  const [opacity, setOpacity] = useState(0.75);
  const [threshold, setThreshold] = useState(0.05);
  const [layers, setLayers] = useState({
    attention: true,
    traffic: true,
    hotspots: true,
  });

  const toggleLayer = (layer) =>
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));

  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    // Dark background
    ctx.fillStyle = "#0f0f1a";
    ctx.fillRect(0, 0, width, height);

    const gw = gridData?.grid_width || 200;
    const gh = gridData?.grid_height || 150;
    const cells = gridData?.cells || [];
    const cellW = width / gw;
    const cellH = height / gh;

    // ── Layer 1: Attention Density ────────────────────────────
    if (layers.attention && cells.length > 0) {
      const stops = COLORMAPS[colormap] || COLORMAPS.JET;
      for (const cell of cells) {
        if (cell.intensity < threshold) continue;
        const [r, g, b] = interpolateColor(stops, cell.intensity);
        ctx.fillStyle = `rgba(${r},${g},${b},${opacity})`;
        // Draw slightly oversized for smooth blending
        ctx.fillRect(
          cell.x * cellW - cellW * 0.3,
          cell.y * cellH - cellH * 0.3,
          cellW * 1.6,
          cellH * 1.6
        );
      }
    }

    // ── Layer 2: Traffic Flow Vectors ─────────────────────────
    if (layers.traffic && flowVectors && flowVectors.length > 0) {
      ctx.strokeStyle = "rgba(0, 200, 255, 0.4)";
      ctx.lineWidth = 1.5;
      for (const vec of flowVectors) {
        const sx = vec.x * cellW;
        const sy = vec.y * cellH;
        const ex = sx + vec.dx * cellW * 3;
        const ey = sy + vec.dy * cellH * 3;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }
    }

    // ── Layer 3: Hotspot Zones ────────────────────────────────
    if (layers.hotspots && hotspotZones && hotspotZones.length > 0) {
      const zoneColors = {
        HOTSPOT: "rgba(255, 60, 60, 0.5)",
        CONVERSION_ZONE: "rgba(60, 200, 60, 0.5)",
        TRANSIT_CORRIDOR: "rgba(60, 140, 255, 0.3)",
        DEAD_ZONE: "rgba(128, 128, 128, 0.4)",
      };
      const zoneBorders = {
        HOTSPOT: "#ff3c3c",
        CONVERSION_ZONE: "#3cc83c",
        TRANSIT_CORRIDOR: "#3c8cff",
        DEAD_ZONE: "#808080",
      };

      for (const zone of hotspotZones) {
        const cx = zone.center_x * width;
        const cy = zone.center_y * height;
        const r = Math.max(width, height) * 0.04;

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = zoneColors[zone.zone_type] || "rgba(200,200,200,0.3)";
        ctx.fill();
        ctx.strokeStyle = zoneBorders[zone.zone_type] || "#ccc";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        ctx.fillStyle = "#fff";
        ctx.font = "bold 10px Inter, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(zone.zone_type.replace("_", " "), cx, cy + r + 14);
      }
    }
  }, [gridData, flowVectors, hotspotZones, colormap, opacity, threshold, layers, width, height]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ── Controls Bar ─────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-900/60 border border-gray-800/60 rounded-xl p-3">
        {/* Colormap Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Colormap</span>
          <div className="flex gap-1">
            {Object.keys(COLORMAPS).map((cm) => (
              <button
                key={cm}
                onClick={() => setColormap(cm)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-semibold transition-all ${
                  colormap === cm
                    ? "bg-violet-600/90 text-white shadow-lg shadow-violet-600/30"
                    : "bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700"
                }`}
              >
                {cm}
              </button>
            ))}
          </div>
        </div>

        {/* Opacity Slider */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Opacity</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-20 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-violet-500"
          />
          <span className="text-[10px] font-mono text-gray-400 w-8">{(opacity * 100).toFixed(0)}%</span>
        </div>

        {/* Threshold Slider */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Threshold</span>
          <input
            type="range"
            min="0"
            max="0.5"
            step="0.01"
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="w-20 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
          <span className="text-[10px] font-mono text-gray-400 w-8">{(threshold * 100).toFixed(0)}%</span>
        </div>

        {/* Layer Toggles */}
        <div className="flex items-center gap-2 ml-auto">
          {[
            { key: "attention", label: "Gaze", emoji: "👁️", color: "violet" },
            { key: "traffic", label: "Traffic", emoji: "🚶", color: "cyan" },
            { key: "hotspots", label: "Hotspots", emoji: "🔥", color: "rose" },
          ].map(({ key, label, emoji, color }) => (
            <button
              key={key}
              onClick={() => toggleLayer(key)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-all border ${
                layers[key]
                  ? `bg-${color}-500/15 text-${color}-400 border-${color}-500/30`
                  : "bg-gray-800/50 text-gray-500 border-transparent"
              }`}
              style={
                layers[key]
                  ? {
                      backgroundColor: color === "violet" ? "rgba(139,92,246,0.15)" :
                                       color === "cyan" ? "rgba(6,182,212,0.15)" :
                                       "rgba(244,63,94,0.15)",
                      color: color === "violet" ? "#a78bfa" :
                             color === "cyan" ? "#22d3ee" :
                             "#fb7185",
                      borderColor: color === "violet" ? "rgba(139,92,246,0.3)" :
                                   color === "cyan" ? "rgba(6,182,212,0.3)" :
                                   "rgba(244,63,94,0.3)",
                    }
                  : {}
              }
            >
              <span>{emoji}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Canvas ────────────────────────────────────────────── */}
      <div className="relative bg-gray-950 border border-gray-800/60 rounded-xl overflow-hidden shadow-xl">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="w-full"
          style={{ aspectRatio: `${width}/${height}` }}
        />
        {/* Metadata overlay */}
        <div className="absolute bottom-2 left-2 flex items-center gap-2">
          <span className="text-[9px] font-mono text-gray-500 bg-black/60 px-2 py-0.5 rounded">
            {gridData?.total_cells || gridData?.cells?.length || 0} cells
          </span>
          <span className="text-[9px] font-mono text-gray-500 bg-black/60 px-2 py-0.5 rounded">
            {colormap}
          </span>
        </div>
      </div>
    </div>
  );
}
