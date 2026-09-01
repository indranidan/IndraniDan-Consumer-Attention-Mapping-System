import React, { useState, useEffect } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Cell
} from "recharts";
import {
  getScoringAnalysis,
  getScoringLeaderboard,
  runScoringAnalysis,
  invalidateScoringCache
} from "../../services/scoringService";

function ScoreBadge({ score }) {
  const num = typeof score === "number" ? score : parseFloat(score) || 0;
  let color = "text-gray-400 bg-gray-500/10 border-gray-500/20";
  if (num >= 70) {
    color = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  } else if (num >= 40) {
    color = "text-amber-400 bg-amber-500/10 border-amber-500/20";
  } else if (num > 0) {
    color = "text-cyan-400 bg-cyan-500/10 border-cyan-500/20";
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold font-mono border ${color}`}>
      {num.toFixed(1)}
    </span>
  );
}

// Custom High-Contrast Tooltip for Scatter Yield Matrix
function CustomScatterTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload;
  if (!data) return null;

  return (
    <div className="p-3.5 bg-gray-950/95 border border-gray-700/90 rounded-xl shadow-2xl backdrop-blur-md text-xs space-y-2 min-w-[200px] pointer-events-none">
      <div className="font-bold text-white text-sm pb-1.5 border-b border-gray-800 flex items-center justify-between gap-2">
        <span className="truncate max-w-[140px] text-gray-100">{data.name}</span>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
          data.rating === 'A' ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
          data.rating === 'B' ? "bg-sky-500/20 text-sky-400 border border-sky-500/30" :
          data.rating === 'C' ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
          "bg-red-500/20 text-red-400 border border-red-500/30"
        }`}>
          {data.rating}
        </span>
      </div>
      <div className="flex justify-between items-center text-gray-200">
        <span className="text-gray-400 font-medium">Attractiveness:</span>
        <span className="font-mono font-bold text-violet-400">
          {typeof data.y === 'number' ? data.y.toFixed(1) : data.y} / 100
        </span>
      </div>
      <div className="flex justify-between items-center text-gray-200">
        <span className="text-gray-400 font-medium">Foot Traffic:</span>
        <span className="font-mono font-semibold text-emerald-400">{data.x} viewers</span>
      </div>
      <div className="flex justify-between items-center text-gray-200">
        <span className="text-gray-400 font-medium">Interactions:</span>
        <span className="font-mono font-semibold text-sky-400">{data.z} events</span>
      </div>
    </div>
  );
}

export default function ProductScoringAnalytics({ jobId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);

  const loadData = async () => {
    if (!jobId) return;
    try {
      setLoading(true);
      const [scores, leaders] = await Promise.all([
        getScoringAnalysis(jobId),
        getScoringLeaderboard(jobId, 5)
      ]);
      setAnalysis(scores);
      setLeaderboard(leaders);
      if (scores?.products?.length > 0) {
        setSelectedProduct(scores.products[0]);
      }
    } catch (err) {
      setError("Failed to load Module 8 scoring analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [jobId]);

  const handleRecalculate = async () => {
    if (!jobId || refreshing) return;
    try {
      setRefreshing(true);
      setError(null);
      invalidateScoringCache(`scores:${jobId}`);
      invalidateScoringCache(`leaderboard:${jobId}`);
      await runScoringAnalysis(jobId);
      const [scores, leaders] = await Promise.all([
        getScoringAnalysis(jobId),
        getScoringLeaderboard(jobId, 5)
      ]);
      setAnalysis(scores);
      setLeaderboard(leaders);
      if (scores?.products?.length > 0) {
        setSelectedProduct(scores.products[0]);
      }
    } catch (err) {
      setError("Failed to recalculate scoring analysis.");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <svg className="w-8 h-8 animate-spin text-violet-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-400 bg-red-500/10 rounded-2xl">{error}</div>;
  }

  if (!analysis) return null;

  // Radar chart data for the selected product
  const radarData = selectedProduct ? [
    { subject: "Attention", A: selectedProduct.pillar_scores.attention_score, fullMark: 100 },
    { subject: "Interaction", A: selectedProduct.pillar_scores.interaction_score, fullMark: 100 },
    { subject: "Pickup", A: selectedProduct.pillar_scores.pickup_score, fullMark: 100 },
    { subject: "Conversion", A: selectedProduct.pillar_scores.conversion_score, fullMark: 100 },
    { subject: "Repeat", A: selectedProduct.pillar_scores.repeat_score, fullMark: 100 },
  ] : [];

  // Scatter chart data (Traffic vs Yield)
  const scatterData = analysis.products.map(p => ({
    name: p.product_name,
    x: p.total_viewers, // Traffic (Opportunities)
    y: p.pillar_scores.composite_score, // Yield (Attractiveness)
    z: p.total_interactions + p.total_pickups, // Bubble size
    rating: p.rating
  }));

  const ratingColors = {
    "A": "#10b981", // Emerald
    "B": "#0ea5e9", // Sky
    "C": "#f59e0b", // Amber
    "D": "#ef4444"  // Red
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Header with KPI stats and Re-evaluate button */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-gray-900/60 border border-gray-800/80">
        <div className="flex flex-wrap items-center gap-6 text-xs">
          <div>
            <span className="text-gray-400">Products Scored: </span>
            <span className="font-bold text-white font-mono">{analysis.summary?.total_products_scored || 0}</span>
          </div>
          <div>
            <span className="text-gray-400">Avg Attractiveness: </span>
            <span className="font-bold text-emerald-400 font-mono">
              {(analysis.summary?.average_attractiveness_score || 0).toFixed(1)} / 100
            </span>
          </div>
          {analysis.summary?.top_performer_name && (
            <div>
              <span className="text-gray-400">Top Performer: </span>
              <span className="font-semibold text-white">
                {analysis.summary.top_performer_name} ({(analysis.summary.top_performer_score || 0).toFixed(1)})
              </span>
            </div>
          )}
        </div>

        <button
          onClick={handleRecalculate}
          disabled={refreshing}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-md ${
            refreshing
              ? "bg-violet-600/50 text-violet-200 cursor-not-allowed"
              : "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white shadow-violet-600/20"
          }`}
          title="Re-compute all 5-pillar product attractiveness scores using updated telemetry"
        >
          <svg
            className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span>{refreshing ? "Recalculating..." : "Re-evaluate Scores"}</span>
        </button>
      </div>

      {/* Task 5.1: Insufficient data warning banner */}
      {analysis.summary?.insufficient_data && (
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30">
          <span className="text-amber-400 text-lg mt-0.5">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-amber-400 mb-1">Insufficient Observation Data</p>
            <p className="text-xs text-amber-300/80 leading-relaxed">
              Scores shown are estimated from Bayesian priors and may not reflect actual product performance.
              Configure spatial product mapping or collect more video data for accurate scoring.
            </p>
          </div>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Leaderboards */}
        <div className="md:col-span-1 flex flex-col gap-6">
          {/* Top Performers */}
          <div className="bg-gray-900/40 border border-gray-800/80 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-emerald-400 mb-4 flex items-center gap-2">
              <span>🏆</span> Top Performers
            </h3>
            <div className="flex flex-col gap-2">
              {leaderboard?.top_performers?.map((p, i) => (
                <div key={p.product_id} className="flex items-center justify-between p-2 rounded-xl bg-gray-800/30">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-500">#{i + 1}</span>
                    <span className="text-sm text-gray-200 font-medium truncate max-w-[120px]" title={p.product_name}>
                      {p.product_name}
                    </span>
                  </div>
                  <ScoreBadge score={p.attractiveness_score} />
                </div>
              ))}
            </div>
          </div>

          {/* Bottom Performers */}
          <div className="bg-gray-900/40 border border-gray-800/80 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-red-400 mb-4 flex items-center gap-2">
              <span>⚠️</span> Needs Attention
            </h3>
            <div className="flex flex-col gap-2">
              {leaderboard?.bottom_performers?.map((p, i) => (
                <div key={p.product_id} className="flex items-center justify-between p-2 rounded-xl bg-gray-800/30">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-500">#{i + 1}</span>
                    <span className="text-sm text-gray-200 font-medium truncate max-w-[120px]" title={p.product_name}>
                      {p.product_name}
                    </span>
                  </div>
                  <ScoreBadge score={p.attractiveness_score} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Radar & Detail */}
        <div className="md:col-span-2 bg-gray-900/40 border border-gray-800/80 rounded-2xl p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-violet-400 flex items-center gap-2">
              <span>🕸️</span> 5-Pillar Product Profile
            </h3>
            <select
              className="bg-gray-950 border border-gray-800 text-sm text-gray-200 rounded-lg px-3 py-1.5 focus:ring-violet-500 focus:border-violet-500"
              value={selectedProduct?.product_id || ""}
              onChange={(e) => {
                const p = analysis.products.find(x => x.product_id === e.target.value);
                if (p) setSelectedProduct(p);
              }}
            >
              {analysis.products.map(p => (
                <option key={p.product_id} value={p.product_id}>{p.product_name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col sm:flex-row gap-6 h-full items-center">
            {/* Radar Chart */}
            <div className="w-full sm:w-1/2 h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#cbd5e1", fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Score" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#030712", borderColor: "#4b5563", borderRadius: "10px", color: "#f3f4f6" }}
                    itemStyle={{ color: "#c4b5fd", fontSize: "12px", fontWeight: "600" }}
                    labelStyle={{ color: "#f9fafb", fontSize: "12px", fontWeight: "bold" }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            
            {/* Detail Stats */}
            <div className="w-full sm:w-1/2 grid grid-cols-2 gap-3">
              <div className="bg-gray-800/40 p-3 rounded-xl border border-gray-700/50">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Composite Score</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white">{selectedProduct?.attractiveness_score.toFixed(1)}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    selectedProduct?.rating === 'A' ? "bg-emerald-500/20 text-emerald-400" :
                    selectedProduct?.rating === 'B' ? "bg-sky-500/20 text-sky-400" :
                    selectedProduct?.rating === 'C' ? "bg-amber-500/20 text-amber-400" :
                    "bg-red-500/20 text-red-400"
                  }`}>{selectedProduct?.rating}</span>
                </div>
              </div>

              <div className="bg-gray-800/40 p-3 rounded-xl border border-gray-700/50">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Intrinsic (Zero-Bias)</div>
                <div className="text-xl font-semibold text-gray-200">
                  {selectedProduct?.intrinsic_attractiveness_score.toFixed(1)}
                </div>
              </div>

              <div className="bg-gray-800/40 p-3 rounded-xl border border-gray-700/50">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Shelf / Tier</div>
                <div className="text-sm font-medium text-gray-300 truncate" title={selectedProduct?.shelf_name}>
                  {selectedProduct?.shelf_name || "Unknown"}
                </div>
                <div className="text-[10px] text-violet-400 font-mono mt-0.5">
                  {selectedProduct?.shelf_visibility.shelf_tier} TIER
                </div>
              </div>

              <div className="bg-gray-800/40 p-3 rounded-xl border border-gray-700/50">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Confidence</div>
                <div className="text-sm font-medium text-gray-300">
                  {selectedProduct?.confidence.confidence_level}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">
                  n={selectedProduct?.confidence.sample_size} views
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Traffic vs Yield Scatter Matrix */}
      <div className="bg-gray-900/40 border border-gray-800/80 rounded-2xl p-5 h-[400px]">
        <h3 className="text-sm font-semibold text-sky-400 mb-6 flex items-center gap-2">
          <span>📈</span> Traffic vs Attractiveness Yield Matrix
        </h3>
        <ResponsiveContainer width="100%" height="90%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 25, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              type="number" 
              dataKey="x" 
              name="Traffic (Viewers)" 
              stroke="#94a3b8" 
              tick={{ fill: "#cbd5e1", fontSize: 11 }}
              label={{ value: "Foot Traffic (Viewers)", position: "insideBottom", offset: -12, fill: "#cbd5e1", fontSize: 12, fontWeight: 500 }} 
            />
            <YAxis 
              type="number" 
              dataKey="y" 
              name="Attractiveness Score" 
              stroke="#94a3b8"
              domain={[0, 100]}
              tick={{ fill: "#cbd5e1", fontSize: 11 }}
              label={{ value: "Attractiveness Score (0-100)", angle: -90, position: "insideLeft", offset: 5, fill: "#cbd5e1", fontSize: 12, fontWeight: 500 }} 
            />
            <ZAxis type="number" dataKey="z" range={[60, 400]} name="Interactions" />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3', stroke: '#64748b' }}
              content={<CustomScatterTooltip />}
            />
            <Scatter name="Products" data={scatterData}>
              {scatterData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={ratingColors[entry.rating] || "#8b5cf6"} fillOpacity={0.85} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
