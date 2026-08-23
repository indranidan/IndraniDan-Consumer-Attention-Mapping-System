/**
 * Zone Canvas Annotator Component
 * =================================
 * Interactive SVG/Canvas visual zone calibration tool for retail video analysis.
 * - Extracts first video frame snapshot on client-side (0ms latency).
 * - Multi-category spatial annotation: Zones, Shelves, Entry, Exit regions.
 * - Rectangle drag-and-drop & multi-vertex polygon drawing modes.
 * - Vertex handle dragging & whole-polygon repositioning.
 * - Resolution-independent 0.0 - 1.0 normalized coordinates.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from "react";

const CATEGORIES = {
  zone: {
    label: "Store Zone / Aisle",
    color: "#06b6d4", // Cyan
    fill: "rgba(6, 182, 212, 0.18)",
    border: "#06b6d4",
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    icon: "🏬",
  },
  shelf: {
    label: "Retail Shelf",
    color: "#a855f7", // Purple
    fill: "rgba(168, 85, 247, 0.22)",
    border: "#a855f7",
    badge: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    icon: "📦",
  },
  entry: {
    label: "Entry Door",
    color: "#10b981", // Emerald
    fill: "rgba(16, 185, 129, 0.18)",
    border: "#10b981",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    icon: "🚪",
  },
  exit: {
    label: "Exit Door",
    color: "#ef4444", // Red
    fill: "rgba(239, 68, 68, 0.18)",
    border: "#ef4444",
    badge: "bg-red-500/10 text-red-400 border-red-500/20",
    icon: "🚶",
  },
};

const DEFAULT_PRESET_REGIONS = [
  {
    id: "zone_beverage",
    name: "Beverage Section",
    category: "zone",
    points: [
      { x: 0.1, y: 0.15 },
      { x: 0.45, y: 0.15 },
      { x: 0.45, y: 0.5 },
      { x: 0.1, y: 0.5 },
    ],
  },
  {
    id: "zone_snacks",
    name: "Snacks Aisle",
    category: "zone",
    points: [
      { x: 0.52, y: 0.15 },
      { x: 0.9, y: 0.15 },
      { x: 0.9, y: 0.5 },
      { x: 0.52, y: 0.5 },
    ],
  },
  {
    id: "shelf_soft_drinks",
    name: "Soft Drinks Tier",
    category: "shelf",
    points: [
      { x: 0.12, y: 0.2 },
      { x: 0.42, y: 0.2 },
      { x: 0.42, y: 0.42 },
      { x: 0.12, y: 0.42 },
    ],
  },
  {
    id: "main_entry",
    name: "Main Entrance",
    category: "entry",
    points: [
      { x: 0.02, y: 0.55 },
      { x: 0.15, y: 0.55 },
      { x: 0.15, y: 0.9 },
      { x: 0.02, y: 0.9 },
    ],
  },
  {
    id: "main_exit",
    name: "Main Exit",
    category: "exit",
    points: [
      { x: 0.85, y: 0.55 },
      { x: 0.98, y: 0.55 },
      { x: 0.98, y: 0.9 },
      { x: 0.85, y: 0.9 },
    ],
  },
];

export default function ZoneCanvasAnnotator({
  videoFile,
  initialConfig,
  onChange,
  onCancel,
}) {
  const [frameImage, setFrameImage] = useState(null);
  const [frameResolution, setFrameResolution] = useState({ width: 1920, height: 1080 });
  const [extractingFrame, setExtractingFrame] = useState(false);

  // Calibration regions state
  const [regions, setRegions] = useState(() => {
    if (initialConfig && Array.isArray(initialConfig.zones)) {
      const items = [];
      (initialConfig.zones || []).forEach((z, i) =>
        items.push({
          id: z.id || `zone_${i + 1}`,
          name: z.name || `Zone ${i + 1}`,
          category: "zone",
          points: (z.polygon || []).map(([x, y]) => ({ x: Number(x), y: Number(y) })),
        })
      );
      (initialConfig.shelves || initialConfig.regions || []).forEach((s, i) =>
        items.push({
          id: s.id || `shelf_${i + 1}`,
          name: s.name || `Shelf ${i + 1}`,
          category: "shelf",
          points: (s.polygon || []).map(([x, y]) => ({ x: Number(x), y: Number(y) })),
        })
      );
      (initialConfig.entry_regions || []).forEach((e, i) =>
        items.push({
          id: e.id || `entry_${i + 1}`,
          name: e.name || `Entry ${i + 1}`,
          category: "entry",
          points: (e.polygon || []).map(([x, y]) => ({ x: Number(x), y: Number(y) })),
        })
      );
      (initialConfig.exit_regions || []).forEach((x, i) =>
        items.push({
          id: x.id || `exit_${i + 1}`,
          name: x.name || `Exit ${i + 1}`,
          category: "exit",
          points: (x.polygon || []).map(([px, py]) => ({ x: Number(px), y: Number(py) })),
        })
      );
      return items.length > 0 ? items : DEFAULT_PRESET_REGIONS;
    }
    return DEFAULT_PRESET_REGIONS;
  });

  const [selectedId, setSelectedId] = useState(regions[0]?.id || null);
  const [toolMode, setToolMode] = useState("select"); // "select" | "rect" | "polygon"
  const [activeCategory, setActiveCategory] = useState("zone");

  // Interaction dragging states
  const [drawingPoints, setDrawingPoints] = useState([]);
  const [dragInfo, setDragInfo] = useState(null); // { type: 'handle'|'shape', regionId, pointIdx, startNormX, startNormY, originPoints }
  const [history, setHistory] = useState([]);

  const containerRef = useRef(null);
  const hiddenVideoRef = useRef(null);

  // Push state to history for undo
  const saveStateToHistory = useCallback(() => {
    setHistory((prev) => [...prev.slice(-15), JSON.stringify(regions)]);
  }, [regions]);

  const handleUndo = () => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    try {
      setRegions(JSON.parse(last));
    } catch {
      // ignore
    }
  };

  // Extract frame snapshot from videoFile
  useEffect(() => {
    if (!videoFile) {
      setFrameImage(null);
      return;
    }

    setExtractingFrame(true);
    const videoUrl = URL.createObjectURL(videoFile);
    const video = document.createElement("video");
    video.src = videoUrl;
    video.crossOrigin = "anonymous";
    video.muted = true;
    video.playsInline = true;

    const handleLoadedMetadata = () => {
      setFrameResolution({
        width: video.videoWidth || 1920,
        height: video.videoHeight || 1080,
      });
      video.currentTime = Math.min(0.5, (video.duration || 1) / 2);
    };

    const handleSeeked = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        setFrameImage(dataUrl);
      } catch (err) {
        console.warn("Could not capture video frame client-side:", err);
      } finally {
        setExtractingFrame(false);
        URL.revokeObjectURL(videoUrl);
      }
    };

    const handleError = () => {
      setExtractingFrame(false);
      URL.revokeObjectURL(videoUrl);
    };

    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("seeked", handleSeeked);
    video.addEventListener("error", handleError);

    return () => {
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("seeked", handleSeeked);
      video.removeEventListener("error", handleError);
    };
  }, [videoFile]);

  // Convert SVG coordinates to normalized [0.0 - 1.0]
  const getNormalizedPoint = useCallback((e) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.clientX ?? (e.touches && e.touches[0]?.clientX);
    const clientY = e.clientY ?? (e.touches && e.touches[0]?.clientY);
    const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
    return { x: Number(x.toFixed(4)), y: Number(y.toFixed(4)) };
  }, []);

  // Sync out formatted configuration
  const formattedConfig = useMemo(() => {
    return {
      zones: regions
        .filter((r) => r.category === "zone")
        .map((r) => ({
          id: r.id,
          name: r.name,
          polygon: r.points.map((p) => [p.x, p.y]),
        })),
      shelves: regions
        .filter((r) => r.category === "shelf")
        .map((r) => ({
          id: r.id,
          name: r.name,
          type: "shelf",
          polygon: r.points.map((p) => [p.x, p.y]),
        })),
      entry_regions: regions
        .filter((r) => r.category === "entry")
        .map((r) => ({
          id: r.id,
          name: r.name,
          polygon: r.points.map((p) => [p.x, p.y]),
        })),
      exit_regions: regions
        .filter((r) => r.category === "exit")
        .map((r) => ({
          id: r.id,
          name: r.name,
          polygon: r.points.map((p) => [p.x, p.y]),
        })),
    };
  }, [regions]);

  useEffect(() => {
    if (onChange) {
      onChange(formattedConfig);
    }
  }, [formattedConfig, onChange]);

  // Handle Canvas Mouse Down
  const handleMouseDown = (e) => {
    const pt = getNormalizedPoint(e);

    if (toolMode === "rect") {
      saveStateToHistory();
      const newId = `${activeCategory}_${Date.now()}`;
      const newRegion = {
        id: newId,
        name: `New ${CATEGORIES[activeCategory].label} ${regions.length + 1}`,
        category: activeCategory,
        points: [
          { x: pt.x, y: pt.y },
          { x: pt.x + 0.01, y: pt.y },
          { x: pt.x + 0.01, y: pt.y + 0.01 },
          { x: pt.x, y: pt.y + 0.01 },
        ],
      };
      setRegions((prev) => [...prev, newRegion]);
      setSelectedId(newId);
      setDragInfo({
        type: "rect-create",
        regionId: newId,
        originX: pt.x,
        originY: pt.y,
      });
      return;
    }

    if (toolMode === "polygon") {
      if (drawingPoints.length >= 3) {
        // Check if clicked near first point to close polygon
        const firstPt = drawingPoints[0];
        const dist = Math.hypot(pt.x - firstPt.x, pt.y - firstPt.y);
        if (dist < 0.04) {
          finishPolygon();
          return;
        }
      }
      setDrawingPoints((prev) => [...prev, pt]);
      return;
    }
  };

  const handleMouseMove = (e) => {
    if (!dragInfo) return;
    const pt = getNormalizedPoint(e);

    if (dragInfo.type === "rect-create") {
      const minX = Math.min(dragInfo.originX, pt.x);
      const maxX = Math.max(dragInfo.originX, pt.x);
      const minY = Math.min(dragInfo.originY, pt.y);
      const maxY = Math.max(dragInfo.originY, pt.y);

      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== dragInfo.regionId) return r;
          return {
            ...r,
            points: [
              { x: minX, y: minY },
              { x: maxX, y: minY },
              { x: maxX, y: maxY },
              { x: minX, y: maxY },
            ],
          };
        })
      );
      return;
    }

    if (dragInfo.type === "handle") {
      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== dragInfo.regionId) return r;
          const nextPoints = [...r.points];
          nextPoints[dragInfo.pointIdx] = { x: pt.x, y: pt.y };
          return { ...r, points: nextPoints };
        })
      );
      return;
    }

    if (dragInfo.type === "shape") {
      const dx = pt.x - dragInfo.startNormX;
      const dy = pt.y - dragInfo.startNormY;

      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== dragInfo.regionId) return r;
          const nextPoints = dragInfo.originPoints.map((p) => ({
            x: Math.max(0, Math.min(1, Number((p.x + dx).toFixed(4)))),
            y: Math.max(0, Math.min(1, Number((p.y + dy).toFixed(4)))),
          }));
          return { ...r, points: nextPoints };
        })
      );
    }
  };

  const handleMouseUp = () => {
    if (dragInfo?.type === "rect-create") {
      setToolMode("select");
    }
    setDragInfo(null);
  };

  const finishPolygon = () => {
    if (drawingPoints.length < 3) {
      setDrawingPoints([]);
      setToolMode("select");
      return;
    }
    saveStateToHistory();
    const newId = `${activeCategory}_${Date.now()}`;
    const newRegion = {
      id: newId,
      name: `Custom ${CATEGORIES[activeCategory].label} ${regions.length + 1}`,
      category: activeCategory,
      points: drawingPoints,
    };
    setRegions((prev) => [...prev, newRegion]);
    setSelectedId(newId);
    setDrawingPoints([]);
    setToolMode("select");
  };

  const handleDeleteSelected = (idToDelete) => {
    const targetId = idToDelete || selectedId;
    if (!targetId) return;
    saveStateToHistory();
    setRegions((prev) => prev.filter((r) => r.id !== targetId));
    if (selectedId === targetId) {
      setSelectedId(null);
    }
  };

  const handleAddPreset = (category) => {
    saveStateToHistory();
    const newId = `${category}_${Date.now()}`;
    const cx = 0.2 + (regions.length * 0.08) % 0.5;
    const cy = 0.2 + (regions.length * 0.08) % 0.4;
    const w = category === "shelf" ? 0.25 : 0.35;
    const h = category === "shelf" ? 0.2 : 0.3;

    const newRegion = {
      id: newId,
      name: `${CATEGORIES[category].label} ${regions.length + 1}`,
      category: category,
      points: [
        { x: Number(cx.toFixed(3)), y: Number(cy.toFixed(3)) },
        { x: Number((cx + w).toFixed(3)), y: Number(cy.toFixed(3)) },
        { x: Number((cx + w).toFixed(3)), y: Number((cy + h).toFixed(3)) },
        { x: Number(cx.toFixed(3)), y: Number((cy + h).toFixed(3)) },
      ],
    };
    setRegions((prev) => [...prev, newRegion]);
    setSelectedId(newId);
    setToolMode("select");
  };

  const selectedRegion = regions.find((r) => r.id === selectedId);

  return (
    <div className="bg-gray-950 border border-gray-800/80 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
      {/* ── Top Toolbar ────────────────────────────────────────────── */}
      <div className="bg-gray-900/90 border-b border-gray-800 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
            <span>📐</span> Video Zone & Shelf Calibration
          </div>
          {videoFile && (
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              🎬 {videoFile.name} ({frameResolution.width}×{frameResolution.height})
            </span>
          )}
          {extractingFrame && (
            <span className="text-[11px] text-amber-400 animate-pulse flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" /> Extracting preview...
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Drawing Tool Selector */}
          <div className="flex items-center bg-gray-950 p-1 rounded-xl border border-gray-800 text-xs">
            <button
              type="button"
              onClick={() => { setToolMode("select"); setDrawingPoints([]); }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                toolMode === "select"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              👆 Select / Move
            </button>
            <button
              type="button"
              onClick={() => { setToolMode("rect"); setDrawingPoints([]); }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                toolMode === "rect"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              ⬛ Draw Box
            </button>
            <button
              type="button"
              onClick={() => { setToolMode("polygon"); setDrawingPoints([]); }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                toolMode === "polygon"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              ⬟ Draw Polygon
            </button>
          </div>

          {/* Undo button */}
          <button
            type="button"
            onClick={handleUndo}
            disabled={history.length === 0}
            className="px-2.5 py-1 text-xs rounded-xl bg-gray-800/80 text-gray-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed border border-gray-700/50"
            title="Undo last action"
          >
            ↩ Undo
          </button>
        </div>
      </div>

      {/* ── Main Canvas & Sidebar Container ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[460px]">
        {/* Visual Drawing Area (8 Cols) */}
        <div className="lg:col-span-8 bg-black relative flex items-center justify-center p-3 select-none overflow-hidden">
          <div
            ref={containerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            className="relative w-full aspect-video max-h-[500px] rounded-xl overflow-hidden shadow-inner border border-gray-800/80 cursor-crosshair group"
            style={{
              backgroundImage: frameImage
                ? `url(${frameImage})`
                : "radial-gradient(circle at center, #1e293b 0%, #0f172a 100%)",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          >
            {/* Grid Backdrop when no video frame is decoded */}
            {!frameImage && (
              <div className="absolute inset-0 opacity-20 pointer-events-none bg-[linear-gradient(to_right,#38bdf8_1px,transparent_1px),linear-gradient(to_bottom,#38bdf8_1px,transparent_1px)] bg-[size:4rem_4rem]">
                <div className="absolute bottom-3 left-3 text-[11px] text-gray-400 font-mono">
                  🏬 Default Architectural Floor Grid (1920×1080)
                </div>
              </div>
            )}

            {/* Interactive SVG Overlay */}
            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
            >
              {/* Render Configured Regions */}
              {regions.map((region) => {
                const isSelected = region.id === selectedId;
                const cat = CATEGORIES[region.category] || CATEGORIES.zone;
                const ptsStr = region.points
                  .map((p) => `${p.x * 1000},${p.y * 1000}`)
                  .join(" ");

                // Compute Centroid for Label
                const cx = (region.points.reduce((sum, p) => sum + p.x, 0) / region.points.length) * 1000;
                const cy = (region.points.reduce((sum, p) => sum + p.y, 0) / region.points.length) * 1000;

                return (
                  <g key={region.id}>
                    {/* Polygon Body */}
                    <polygon
                      points={ptsStr}
                      fill={isSelected ? cat.fill.replace("0.18", "0.32") : cat.fill}
                      stroke={cat.border}
                      strokeWidth={isSelected ? "3.5" : "2"}
                      strokeDasharray={region.category === "entry" || region.category === "exit" ? "8,5" : "none"}
                      className="transition-all cursor-move"
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        setSelectedId(region.id);
                        if (toolMode === "select") {
                          saveStateToHistory();
                          const pt = getNormalizedPoint(e);
                          setDragInfo({
                            type: "shape",
                            regionId: region.id,
                            startNormX: pt.x,
                            startNormY: pt.y,
                            originPoints: region.points,
                          });
                        }
                      }}
                    />

                    {/* Region Label at Centroid */}
                    <g transform={`translate(${cx}, ${cy})`} className="pointer-events-none">
                      <rect
                        x="-60"
                        y="-12"
                        width="120"
                        height="24"
                        rx="6"
                        fill="#030712"
                        fillOpacity="0.85"
                        stroke={cat.border}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fill="#f8fafc"
                        fontSize="12"
                        fontWeight="600"
                        fontFamily="system-ui"
                      >
                        {cat.icon} {region.name.length > 14 ? region.name.slice(0, 13) + "…" : region.name}
                      </text>
                    </g>

                    {/* Vertex Drag Handles (Only for selected region) */}
                    {isSelected &&
                      region.points.map((p, idx) => (
                        <circle
                          key={idx}
                          cx={p.x * 1000}
                          cy={p.y * 1000}
                          r="8"
                          fill="#ffffff"
                          stroke={cat.border}
                          strokeWidth="3"
                          className="cursor-pointer hover:scale-125 transition-transform drop-shadow-md"
                          onMouseDown={(e) => {
                            e.stopPropagation();
                            saveStateToHistory();
                            setDragInfo({
                              type: "handle",
                              regionId: region.id,
                              pointIdx: idx,
                            });
                          }}
                        />
                      ))}
                  </g>
                );
              })}

              {/* In-progress Polygon Drawing Preview */}
              {toolMode === "polygon" && drawingPoints.length > 0 && (
                <g>
                  <polyline
                    points={drawingPoints.map((p) => `${p.x * 1000},${p.y * 1000}`).join(" ")}
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="2.5"
                    strokeDasharray="6,4"
                  />
                  {drawingPoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={p.x * 1000}
                      cy={p.y * 1000}
                      r={idx === 0 ? "9" : "6"}
                      fill={idx === 0 ? "#10b981" : "#38bdf8"}
                      stroke="#ffffff"
                      strokeWidth="2"
                    />
                  ))}
                </g>
              )}
            </svg>

            {/* Drawing Mode floating hint */}
            {toolMode === "polygon" && (
              <div className="absolute top-3 left-3 bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-cyan-500/40 text-xs text-cyan-300 shadow-lg flex items-center gap-2">
                <span>📍 Click to place points ({drawingPoints.length} added). Click start point to close.</span>
                {drawingPoints.length >= 3 && (
                  <button
                    type="button"
                    onClick={finishPolygon}
                    className="px-2 py-0.5 bg-emerald-500 text-white rounded text-[11px] font-bold"
                  >
                    Done ✓
                  </button>
                )}
              </div>
            )}
            {toolMode === "rect" && (
              <div className="absolute top-3 left-3 bg-gray-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-purple-500/40 text-xs text-purple-300 shadow-lg">
                ⬛ Click and drag to draw a bounding rectangle.
              </div>
            )}
          </div>
        </div>

        {/* ── Region List & Properties Sidebar (4 Cols) ───────────── */}
        <div className="lg:col-span-4 bg-gray-900/80 border-t lg:border-t-0 lg:border-l border-gray-800 flex flex-col justify-between p-4 space-y-4">
          <div className="space-y-4 overflow-y-auto max-h-[420px] pr-1">
            {/* Quick Add Presets Bar */}
            <div>
              <label className="text-[11px] text-gray-400 uppercase font-semibold tracking-wider block mb-2">
                ➕ Quick Add Retail Elements
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => handleAddPreset("zone")}
                  className="px-2.5 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-medium flex items-center justify-center gap-1 transition-all"
                >
                  <span>🟦</span> + Zone
                </button>
                <button
                  type="button"
                  onClick={() => handleAddPreset("shelf")}
                  className="px-2.5 py-1.5 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-medium flex items-center justify-center gap-1 transition-all"
                >
                  <span>🟪</span> + Shelf
                </button>
                <button
                  type="button"
                  onClick={() => handleAddPreset("entry")}
                  className="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-medium flex items-center justify-center gap-1 transition-all"
                >
                  <span>🟩</span> + Entry
                </button>
                <button
                  type="button"
                  onClick={() => handleAddPreset("exit")}
                  className="px-2.5 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 text-xs font-medium flex items-center justify-center gap-1 transition-all"
                >
                  <span>🟥</span> + Exit
                </button>
              </div>
            </div>

            {/* Selected Region Editor */}
            {selectedRegion ? (
              <div className="bg-gray-950 p-3.5 rounded-xl border border-gray-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>{CATEGORIES[selectedRegion.category]?.icon}</span> Edit Selected Region
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteSelected(selectedRegion.id)}
                    className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
                  >
                    🗑️ Delete
                  </button>
                </div>

                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">
                    Region Name
                  </label>
                  <input
                    type="text"
                    value={selectedRegion.name}
                    onChange={(e) => {
                      const val = e.target.value;
                      setRegions((prev) =>
                        prev.map((r) => (r.id === selectedRegion.id ? { ...r, name: val } : r))
                      );
                    }}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-[10px] text-gray-500 uppercase tracking-wider block mb-1">
                    Category Type
                  </label>
                  <select
                    value={selectedRegion.category}
                    onChange={(e) => {
                      const cat = e.target.value;
                      setRegions((prev) =>
                        prev.map((r) => (r.id === selectedRegion.id ? { ...r, category: cat } : r))
                      );
                    }}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="zone">Store Zone / Aisle (Phase 3 & 4)</option>
                    <option value="shelf">Retail Shelf / Display (Phase 5 Attention)</option>
                    <option value="entry">Entry Door (Phase 3 Entry Traffic)</option>
                    <option value="exit">Exit Door (Phase 3 Journey Exit)</option>
                  </select>
                </div>

                <div className="text-[11px] text-gray-500 flex justify-between">
                  <span>Vertices: {selectedRegion.points.length} points</span>
                  <span>Normalized: (0.0 - 1.0)</span>
                </div>
              </div>
            ) : (
              <div className="bg-gray-950/60 p-3 rounded-xl border border-dashed border-gray-800 text-center text-xs text-gray-500">
                👆 Click on any box on the canvas or pick from the list below to edit.
              </div>
            )}

            {/* List of Regions */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-400 uppercase font-semibold tracking-wider">
                  Configured Regions ({regions.length})
                </span>
                {regions.length > 0 && (
                  <button
                    type="button"
                    onClick={() => { saveStateToHistory(); setRegions([]); setSelectedId(null); }}
                    className="text-[10px] text-gray-500 hover:text-red-400"
                  >
                    Clear All
                  </button>
                )}
              </div>

              <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
                {regions.map((r) => {
                  const cat = CATEGORIES[r.category] || CATEGORIES.zone;
                  const isSel = r.id === selectedId;
                  return (
                    <div
                      key={r.id}
                      onClick={() => setSelectedId(r.id)}
                      className={`px-2.5 py-2 rounded-xl text-xs flex items-center justify-between cursor-pointer border transition-all ${
                        isSel
                          ? "bg-gray-800/90 border-cyan-500/60 text-white shadow-md"
                          : "bg-gray-950/70 border-gray-800/80 text-gray-300 hover:border-gray-700"
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span>{cat.icon}</span>
                        <span className="font-medium truncate">{r.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] border ${cat.badge}`}>
                          {r.category.toUpperCase()}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSelected(r.id);
                          }}
                          className="text-gray-500 hover:text-red-400 p-0.5"
                          title="Delete region"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Bottom Guidance Info */}
          <div className="pt-2 border-t border-gray-800/80 text-[11px] text-gray-400 flex items-center justify-between">
            <span>💡 All coordinates are normalized to video dimensions.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
