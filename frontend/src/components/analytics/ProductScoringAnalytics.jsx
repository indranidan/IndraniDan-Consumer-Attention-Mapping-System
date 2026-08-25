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
import { getScoringAnalysis, getScoringLeaderboard } from "../../services/scoringService";

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

export default function ProductScoringAnalytics({ jobId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);

  useEffect(() => {
    async function loadData() {
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
    }
    loadData();
  }, [jobId]);

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
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Score" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "8px" }}
                    itemStyle={{ color: "#c4b5fd" }}
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
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              type="number" 
              dataKey="x" 
              name="Traffic (Viewers)" 
              stroke="#9ca3af" 
              label={{ value: "Foot Traffic (Viewers)", position: "insideBottom", offset: -10, fill: "#9ca3af", fontSize: 12 }} 
            />
            <YAxis 
              type="number" 
              dataKey="y" 
              name="Attractiveness Score" 
              stroke="#9ca3af"
              domain={[0, 100]}
              label={{ value: "Score", angle: -90, position: "insideLeft", fill: "#9ca3af", fontSize: 12 }} 
            />
            <ZAxis type="number" dataKey="z" range={[50, 400]} name="Interactions" />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "8px" }}
              formatter={(value, name, props) => {
                if (name === "Attractiveness Score") return [value.toFixed(1), name];
                return [value, name];
              }}
            />
            <Scatter name="Products" data={scatterData}>
              {scatterData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={ratingColors[entry.rating] || "#8b5cf6"} fillOpacity={0.7} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
