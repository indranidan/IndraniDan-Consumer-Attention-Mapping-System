import React from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import { ScoreBadge } from './SharedComponents';

export default function MatrixTab() {
  const {
    unifiedData,
    matrixSearch,
    setMatrixSearch,
    matrixView,
    setMatrixView
  } = useUnifiedJobContext();

  const m4Analysis = unifiedData?.attention || {};
  const m4Shelves = m4Analysis.shelves || [];
  
  const m5Analysis = unifiedData?.interaction || {};
  const m5Products = m5Analysis.products || [];
  const m5Comparisons = m5Analysis.comparisons || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        {/* Matrix View Switcher & Search */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMatrixView("shelves")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                matrixView === "shelves"
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                  : "bg-gray-800/60 text-gray-400 hover:text-white"
              }`}
            >
              Shelves Intelligence ({m4Shelves.length})
            </button>
            <button
              onClick={() => setMatrixView("products")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                matrixView === "products"
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                  : "bg-gray-800/60 text-gray-400 hover:text-white"
              }`}
            >
              Products Engagement ({m5Products.length})
            </button>
            <button
              onClick={() => setMatrixView("comparisons")}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                matrixView === "comparisons"
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                  : "bg-gray-800/60 text-gray-400 hover:text-white"
              }`}
            >
              Consideration Journeys ({m5Comparisons.length})
            </button>
          </div>

          <div className="relative">
            <input
              type="text"
              value={matrixSearch}
              onChange={(e) => setMatrixSearch(e.target.value)}
              placeholder="Search shelf or product..."
              className="bg-gray-950/80 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 w-52"
            />
          </div>
        </div>

        {/* View 1: Shelves Table */}
        {matrixView === "shelves" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-[11px] text-gray-400 uppercase tracking-wider">
                  <th className="py-3 px-3">Shelf Details</th>
                  <th className="py-3 px-3">Zone</th>
                  <th className="py-3 px-3 text-center">Visitors</th>
                  <th className="py-3 px-3 text-center">Gaze Viewers</th>
                  <th className="py-3 px-3 text-right">Attention Time</th>
                  <th className="py-3 px-3 text-right">Engagement Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/40 text-gray-300">
                {m4Shelves
                  .filter((s) =>
                    matrixSearch
                      ? (s.shelf_name || s.shelf_code || "").toLowerCase().includes(matrixSearch.toLowerCase())
                      : true
                  )
                  .map((s, idx) => (
                    <tr key={idx} className="hover:bg-gray-800/20 transition-colors">
                      <td className="py-3 px-3 font-semibold text-white">
                        <p>{s.shelf_name || s.shelf_code}</p>
                        <p className="text-[10px] text-gray-500 font-mono">{s.shelf_code || "ID: " + s.shelf_id}</p>
                      </td>
                      <td className="py-3 px-3 text-gray-400">{s.zone_id || "Main Aisle"}</td>
                      <td className="py-3 px-3 text-center font-mono">{s.total_visitors || 0}</td>
                      <td className="py-3 px-3 text-center font-mono text-cyan-400">{s.unique_viewers || 0}</td>
                      <td className="py-3 px-3 text-right font-mono">
                        {(s.total_attention_duration_sec || 0).toFixed(1)}s
                      </td>
                      <td className="py-3 px-3 text-right">
                        <ScoreBadge score={s.engagement_score || 0} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* View 2: Products Table */}
        {matrixView === "products" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-[11px] text-gray-400 uppercase tracking-wider">
                  <th className="py-3 px-3">Product Name & SKU</th>
                  <th className="py-3 px-3">Assigned Shelf</th>
                  <th className="py-3 px-3 text-center">Total Views</th>
                  <th className="py-3 px-3 text-center">Unique Viewers</th>
                  <th className="py-3 px-3 text-right">Duration</th>
                  <th className="py-3 px-3 text-center">Pickups</th>
                  <th className="py-3 px-3 text-center">Comparisons</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/40 text-gray-300">
                {m5Products
                  .filter((p) =>
                    matrixSearch
                      ? (p.product_name || p.sku || "").toLowerCase().includes(matrixSearch.toLowerCase())
                      : true
                  )
                  .map((p, idx) => (
                    <tr key={idx} className="hover:bg-gray-800/20 transition-colors">
                      <td className="py-3 px-3 font-semibold text-white">
                        <p>{p.product_name}</p>
                        <p className="text-[10px] text-gray-500 font-mono">SKU: {p.sku || "N/A"}</p>
                      </td>
                      <td className="py-3 px-3 text-gray-400">{p.shelf_name || "Shelf " + p.shelf_id}</td>
                      <td className="py-3 px-3 text-center font-mono text-cyan-400 font-bold">{p.total_views || 0}</td>
                      <td className="py-3 px-3 text-center font-mono">{p.unique_viewers || 0}</td>
                      <td className="py-3 px-3 text-right font-mono">
                        {(p.total_engagement_duration_sec || 0).toFixed(1)}s
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-emerald-400">{p.total_pickups || 0}</td>
                      <td className="py-3 px-3 text-center font-mono text-purple-400">{p.total_comparisons || 0}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* View 3: Comparison Journeys */}
        {matrixView === "comparisons" && (
          <div className="space-y-3">
            {m5Comparisons.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-xs">
                No multi-product consideration journeys observed for this session.
              </div>
            ) : (
              m5Comparisons.map((c, idx) => (
                <div
                  key={idx}
                  className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-3.5 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">⚖️</span>
                    <div>
                      <p className="text-xs font-bold text-white">
                        {c.product_a_name} <span className="text-gray-500 font-normal">⟷</span> {c.product_b_name}
                      </p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        Shopper #{c.track_id} alternate fixations across shelf products
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-mono text-violet-400 px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20">
                    {c.switch_count || 1} gaze switches
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
