/**
 * Recommendations Dashboard Component
 * =====================================
 * Module 9 — Prescriptive Merchandising & Optimization Dashboard.
 * Displays prioritized, categorized recommendations with ROI impact projections,
 * action step checklists, and embedded "What-If" Planogram Simulator.
 */

import { useState, useEffect } from "react";
import {
  getJobRecommendations,
  runJobRecommendations,
} from "../../services/recommendationService";
import PlanogramSwapSimulator from "./PlanogramSwapSimulator";

const CATEGORY_TABS = [
  { id: "ALL", label: "All Recommendations", icon: "✨" },
  { id: "SHELF_OPTIMIZATION", label: "Shelf Optimization", icon: "📦" },
  { id: "PRODUCT_PLACEMENT", label: "Product Placement", icon: "🔄" },
  { id: "PROMOTIONAL_PLACEMENT", label: "Promotions & Endcaps", icon: "🏷️" },
  { id: "CONSUMER_ENGAGEMENT", label: "Funnel & Friction", icon: "⚠️" },
  { id: "LAYOUT_IMPROVEMENT", label: "Store Layout", icon: "🗺️" },
];

const PRIORITY_FILTERS = [
  { id: "ALL", label: "All Priorities" },
  { id: "CRITICAL", label: "Critical", color: "bg-red-500/10 text-red-400 border-red-500/30" },
  { id: "HIGH", label: "High", color: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  { id: "MEDIUM", label: "Medium", color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" },
  { id: "LOW", label: "Low", color: "bg-gray-500/10 text-gray-400 border-gray-500/30" },
];

const PRIORITY_BADGES = {
  CRITICAL: "bg-red-500/15 text-red-300 border-red-500/40 shadow-red-500/10 shadow-lg",
  HIGH: "bg-amber-500/15 text-amber-300 border-amber-500/40 shadow-amber-500/10 shadow-lg",
  MEDIUM: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  LOW: "bg-gray-500/15 text-gray-300 border-gray-500/30",
};

const CATEGORY_BADGES = {
  SHELF_OPTIMIZATION: { label: "Shelf Tier Optimization", color: "bg-purple-500/10 text-purple-300 border-purple-500/20" },
  PRODUCT_PLACEMENT: { label: "Product Placement & Swaps", color: "bg-blue-500/10 text-blue-300 border-blue-500/20" },
  PROMOTIONAL_PLACEMENT: { label: "Promotional Feature", color: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" },
  CONSUMER_ENGAGEMENT: { label: "Shopper Friction Fix", color: "bg-rose-500/10 text-rose-300 border-rose-500/20" },
  LAYOUT_IMPROVEMENT: { label: "Store Layout & Traffic", color: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20" },
};

export default function RecommendationsDashboard({ jobId, storeId = null }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const [activeCategory, setActiveCategory] = useState("ALL");
  const [activePriority, setActivePriority] = useState("ALL");
  const [showSimulator, setShowSimulator] = useState(false);
  const [simulatorProduct, setSimulatorProduct] = useState(null);
  const [expandedRecId, setExpandedRecId] = useState(null);

  const fetchRecommendations = async () => {
    if (!jobId) return;
    setLoading(true);
    setError("");
    try {
      const filters = {};
      if (activeCategory !== "ALL") filters.category = activeCategory;
      if (activePriority !== "ALL") filters.priority = activePriority;

      const res = await getJobRecommendations(jobId, filters);
      setData(res);
    } catch (err) {
      console.error("Failed to load recommendations:", err);
      setError(err?.response?.data?.detail || "Failed to load Module 9 recommendations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [jobId, activeCategory, activePriority]);

  const handleRefresh = async () => {
    if (!jobId) return;
    setRefreshing(true);
    setError("");
    try {
      await runJobRecommendations(jobId);
      await fetchRecommendations();
    } catch (err) {
      console.error("Failed to refresh recommendations:", err);
      setError(err?.response?.data?.detail || "Failed to regenerate recommendations");
    } finally {
      setRefreshing(false);
    }
  };

  const handleOpenSimulatorWithRec = (rec) => {
    setSimulatorProduct({
      id: rec.target_id,
      name: rec.target_name,
      current_tier: rec.shelf_swap_details?.from_tier || "BOTTOM",
      target_tier: rec.shelf_swap_details?.to_tier || "EYE_LEVEL",
      attractiveness_score: rec.current_metrics?.observed_attractiveness || 45.0,
      intrinsic_score: rec.current_metrics?.intrinsic_attractiveness || 75.0,
    });
    setShowSimulator(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const recommendations = data?.recommendations || [];
  const summary = data?.summary || {};

  return (
    <div className="space-y-6">
      {/* ── Top Control Bar ───────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gray-900/60 backdrop-blur-xl border border-gray-800/60 rounded-2xl p-5 shadow-xl">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">💡</span>
            <h2 className="text-xl font-bold text-white tracking-wide">
              Prescriptive Merchandising Intelligence
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              MODULE 9
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Algorithmic recommendations for shelf tier rebalancing, opportunity swaps, and friction intervention.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 border transition-all ${
              showSimulator
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-lg shadow-cyan-500/10"
                : "bg-gray-800/80 text-gray-300 border-gray-700 hover:bg-gray-700/80"
            }`}
          >
            <span>🔮</span>
            {showSimulator ? "Hide Simulator" : "What-If Simulator"}
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 flex items-center gap-2 disabled:opacity-50 transition-all cursor-pointer"
          >
            <span className={refreshing ? "animate-spin" : ""}>🔄</span>
            {refreshing ? "Recomputing..." : "Refresh Actions"}
          </button>
        </div>
      </div>

      {/* ── Optional Simulator Section ────────────────────────── */}
      {showSimulator && (
        <div className="animate-fadeIn">
          <PlanogramSwapSimulator initialProduct={simulatorProduct} />
        </div>
      )}

      {/* ── Summary KPI Cards ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-gray-900/60 border border-gray-800/60 rounded-xl p-4">
          <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">
            Total Actionable Items
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {summary.total_recommendations ?? recommendations.length}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Across 5 merchandising areas</div>
        </div>

        <div className="bg-gray-900/60 border border-red-500/20 rounded-xl p-4">
          <div className="text-[11px] font-medium text-red-400 uppercase tracking-wider">
            Critical Bottlenecks
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            {summary.critical_count ?? 0}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Immediate revenue/ROI priority</div>
        </div>

        <div className="bg-gray-900/60 border border-amber-500/20 rounded-xl p-4">
          <div className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">
            High Priority Actions
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {summary.high_count ?? 0}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Significant attention lift</div>
        </div>

        <div className="bg-gray-900/60 border border-emerald-500/20 rounded-xl p-4">
          <div className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">
            Avg Projected Lift
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {summary.average_impact_score ? `+${summary.average_impact_score}%` : "—"}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Composite yield metric</div>
        </div>
      </div>

      {/* ── Filter Bar: Category Tabs & Priority Filter ──────── */}
      <div className="space-y-3">
        {/* Category Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap flex items-center gap-2 border transition-all cursor-pointer ${
                activeCategory === tab.id
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-lg shadow-cyan-500/10"
                  : "bg-gray-900/60 text-gray-400 border-gray-800/80 hover:bg-gray-800/60 hover:text-gray-200"
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Priority Filter Badges */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-gray-500 font-medium mr-1">Filter Priority:</span>
          {PRIORITY_FILTERS.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePriority(p.id)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-all cursor-pointer ${
                activePriority === p.id
                  ? "bg-white/10 text-white border-white/30 font-bold"
                  : "bg-gray-900/40 text-gray-400 border-gray-800 hover:text-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Error & Loading States ────────────────────────────── */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
          ⚠️ {error}
        </div>
      )}

      {loading && !refreshing && (
        <div className="text-center py-16 text-gray-400 text-xs flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
          <span>Evaluating Module 9 prescriptive rules...</span>
        </div>
      )}

      {/* ── Empty State ───────────────────────────────────────── */}
      {!loading && recommendations.length === 0 && (
        <div className="bg-gray-900/40 border border-gray-800/60 rounded-2xl p-12 text-center">
          <span className="text-4xl">🎯</span>
          <h4 className="text-sm font-bold text-white mt-3">No Actionable Recommendations</h4>
          <p className="text-xs text-gray-400 mt-1 max-w-md mx-auto">
            {activeCategory !== "ALL" || activePriority !== "ALL"
              ? "No recommendations match the current filters. Try changing your category or priority filter."
              : "All SKUs appear to be optimized for their current shelf tiers and traffic patterns."}
          </p>
        </div>
      )}

      {/* ── Actionable Recommendations Cards List ─────────────── */}
      <div className="space-y-4">
        {recommendations.map((rec) => {
          const isExpanded = expandedRecId === rec.id;
          const catInfo = CATEGORY_BADGES[rec.category] || { label: rec.category, color: "bg-gray-800 text-gray-300" };
          const priorityStyle = PRIORITY_BADGES[rec.priority] || PRIORITY_BADGES.LOW;

          return (
            <div
              key={rec.id}
              className={`bg-gray-900/70 backdrop-blur-xl border rounded-2xl p-5 transition-all ${
                rec.priority === "CRITICAL"
                  ? "border-red-500/30 hover:border-red-500/50"
                  : rec.priority === "HIGH"
                  ? "border-amber-500/30 hover:border-amber-500/50"
                  : "border-gray-800/80 hover:border-gray-700"
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-gray-800/60">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border uppercase tracking-wider ${priorityStyle}`}>
                    {rec.priority}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${catInfo.color}`}>
                    {catInfo.label}
                  </span>
                  <span className="text-xs text-gray-400">
                    Target: <strong className="text-gray-200">{rec.target_name}</strong>
                  </span>
                </div>

                {/* Impact Lift Pill */}
                {rec.expected_impact && (
                  <div className="flex items-center gap-2">
                    {rec.expected_impact.attention_lift_pct > 0 && (
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        +{rec.expected_impact.attention_lift_pct}% Attention
                      </span>
                    )}
                    {rec.expected_impact.conversion_lift_pct > 0 && (
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        +{rec.expected_impact.conversion_lift_pct}% Conv
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Title & Description */}
              <div className="mt-3">
                <h3 className="text-base font-bold text-white">{rec.title}</h3>
                <p className="text-xs text-gray-300 mt-1 leading-relaxed">{rec.description}</p>
              </div>

              {/* Proposed Action Banner */}
              {rec.proposed_action && (
                <div className="mt-4 p-3 bg-gray-950/60 border border-gray-800 rounded-xl flex items-start gap-2.5">
                  <span className="text-sm mt-0.5">🛠️</span>
                  <div>
                    <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                      Prescribed Action Step
                    </div>
                    <div className="text-xs text-cyan-300 font-medium mt-0.5">
                      {rec.proposed_action}
                    </div>
                  </div>
                </div>
              )}

              {/* Current Metrics Chips */}
              {rec.current_metrics && Object.keys(rec.current_metrics).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(rec.current_metrics).map(([key, val]) => (
                    <span
                      key={key}
                      className="px-2.5 py-1 bg-gray-950/80 border border-gray-800/80 rounded-lg text-[11px] font-mono text-gray-400"
                    >
                      <span className="text-gray-500">{key.replace(/_/g, " ")}:</span>{" "}
                      <strong className="text-gray-200">{String(val)}</strong>
                    </span>
                  ))}
                </div>
              )}

              {/* Collapsible Details & Rationale */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-gray-800/60 space-y-3 text-xs animate-fadeIn">
                  {rec.rationale && (
                    <div className="p-3 bg-blue-950/20 border border-blue-500/20 rounded-xl text-blue-300/90 leading-relaxed">
                      📖 <strong>Analytical Rationale:</strong> {rec.rationale}
                    </div>
                  )}

                  {rec.shelf_swap_details && (
                    <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl text-purple-300/90 flex items-center justify-between">
                      <div>
                        🔄 <strong>Shelf Movement:</strong> {rec.shelf_swap_details.from_tier} (γ={rec.shelf_swap_details.from_gamma}) → {rec.shelf_swap_details.to_tier} (γ={rec.shelf_swap_details.to_gamma})
                      </div>
                      <button
                        onClick={() => handleOpenSimulatorWithRec(rec)}
                        className="px-2.5 py-1 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 rounded-lg text-[11px] font-semibold cursor-pointer"
                      >
                        Simulate in Studio ↗
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Card Footer: Expand toggle & Action Button */}
              <div className="mt-4 pt-3 flex items-center justify-between border-t border-gray-800/40">
                <button
                  onClick={() => setExpandedRecId(isExpanded ? null : rec.id)}
                  className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 font-medium cursor-pointer"
                >
                  <span>{isExpanded ? "▲ Hide Rationale" : "▼ View Analytical Details"}</span>
                </button>

                <button
                  onClick={() => handleOpenSimulatorWithRec(rec)}
                  className="px-3 py-1 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all"
                >
                  <span>🔮</span>
                  <span>Test in What-If Studio</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
