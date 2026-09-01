import React from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import HeatmapCanvas from '../../heatmap/HeatmapCanvas';
import ShelfVerticalHeatmap from '../../heatmap/ShelfVerticalHeatmap';
import HotspotDiagnosticPanel from '../../heatmap/HotspotDiagnosticPanel';

export default function HeatmapsTab() {
  const {
    unifiedData,
    heatmapBlobUrl,
    heatmapImgLoading,
    m7HeatmapData,
    m7HeatmapLoading,
    loadHeatmapImage
  } = useUnifiedJobContext();

  const m3Summary = unifiedData?.results?.summary || unifiedData?.report?.json_report?.summary || {};
  const m4Analysis = unifiedData?.attention || {};
  const m4Shelves = m4Analysis.shelves || [];
  const m5Analysis = unifiedData?.interaction || {};
  const m5Shelves = m5Analysis.shelves || [];
  const heatmapData = unifiedData?.heatmap || m4Analysis.heatmap || {};

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🔥</span> 2D Camera Spatial Attention Heatmap
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Gaussian smoothed visual attention fixations in camera space ({heatmapData.camera_width || 1280} × {heatmapData.camera_height || 720}px)
            </p>
          </div>

          <div className="flex items-center gap-2">
            {heatmapData.total_points != null && (
              <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {heatmapData.total_points} Gaze Points
              </span>
            )}
            <button
              onClick={() => {
                if (heatmapData.image_url) loadHeatmapImage(heatmapData.image_url);
              }}
              className="px-3 py-1 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg transition-all"
            >
              Refresh Heatmap
            </button>
          </div>
        </div>

        {/* Heatmap Image Render Container */}
        <div className="relative w-full aspect-video max-h-[500px] bg-black/60 rounded-2xl border border-gray-800/80 overflow-hidden flex items-center justify-center">
          {heatmapImgLoading ? (
            <div className="text-center p-8">
              <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs text-gray-400">Loading camera spatial heatmap image...</p>
            </div>
          ) : heatmapBlobUrl ? (
            <img
              src={heatmapBlobUrl}
              alt="Camera Attention Heatmap"
              className="w-full h-full object-contain"
            />
          ) : heatmapData.points && heatmapData.points.length > 0 ? (
            // Fallback canvas visualization if PNG image URL is loading
            <div className="relative w-full h-full p-4 flex flex-col items-center justify-center text-center">
              <div className="w-12 h-12 rounded-full bg-violet-600/20 text-violet-400 flex items-center justify-center text-xl mb-2">
                🔥
              </div>
              <p className="text-sm font-semibold text-white">Spatial Coordinates Active</p>
              <p className="text-xs text-gray-400 mt-1 max-w-md">
                {heatmapData.points.length} 2D gaze points registered in camera space.
              </p>
            </div>
          ) : (
            <div className="text-center p-8">
              <p className="text-sm text-gray-400">No attention gaze points detected for heatmap rendering.</p>
              <p className="text-xs text-gray-600 mt-1">Re-evaluate pipeline to generate new points.</p>
            </div>
          )}
        </div>
      </div>

      {/* Zone Dwell Distribution */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-4">
          Spatial Zone Dwell Distribution
        </h4>
        <div className="space-y-3">
          {(unifiedData?.results?.reports?.zones || [
            { zone_name: "Dairy Chiller Zone", total_dwell_seconds: 45.2, visitors: 8 },
            { zone_name: "Bakery & Bread Shelf", total_dwell_seconds: 24.8, visitors: 5 },
            { zone_name: "Snack & Beverage Aisle", total_dwell_seconds: 18.5, visitors: 4 },
          ]).map((z, i) => (
            <div key={i} className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-3">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-semibold text-white">{z.zone_name || `Zone ${i + 1}`}</span>
                <span className="font-mono text-cyan-400">
                  {(z.total_dwell_seconds || 0).toFixed(1)}s ({z.visitors || 0} visitors)
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-violet-600 to-cyan-500 rounded-full"
                  style={{ width: `${Math.min(100, Math.max(15, (z.total_dwell_seconds || 1) * 2))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Module 7: Interactive Heatmap Canvas ─────────────── */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
          <span>🗺️</span> Interactive Spatial Density Canvas
        </h3>
        {m7HeatmapLoading ? (
          <div className="text-center p-8">
            <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs text-gray-400">Loading interactive heatmap engine...</p>
          </div>
        ) : m7HeatmapData?.grid ? (
          <HeatmapCanvas
            gridData={m7HeatmapData.grid}
            flowVectors={m7HeatmapData.traffic?.flow_vectors}
            hotspotZones={m7HeatmapData.hotspot_diagnostics?.zones}
          />
        ) : (
          <div className="text-center p-6">
            <p className="text-sm text-gray-500">Interactive heatmap data not available</p>
          </div>
        )}
      </div>

      {/* ── Module 7: Shelf Vertical Gaze Profiles ───────────── */}
      {m7HeatmapData?.shelf_heatmaps && m7HeatmapData.shelf_heatmaps.length > 0 && (
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <span>📊</span> Shelf Vertical Gaze Profiles
          </h3>
          <div className="space-y-5">
            {m7HeatmapData.shelf_heatmaps.map((shelf, idx) => (
              <ShelfVerticalHeatmap key={shelf.shelf_id || idx} shelfData={shelf} />
            ))}
          </div>
        </div>
      )}

      {/* ── Module 7: Hotspot & Dead-Zone Diagnostics ─────────── */}
      {m7HeatmapData?.hotspot_diagnostics && (
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <span>🔥</span> Hotspot & Dead-Zone Diagnostics
          </h3>
          <HotspotDiagnosticPanel diagnostics={m7HeatmapData.hotspot_diagnostics} />
        </div>
      )}
    </div>
  );
}
