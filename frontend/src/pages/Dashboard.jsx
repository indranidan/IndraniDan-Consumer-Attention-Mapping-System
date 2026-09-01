/**
 * Retail Intelligence Executive Command Center
 * ==============================================
 * Comprehensive executive single-pane-of-glass dashboard consolidating:
 * - Module 3: Shopper Footfall & Trajectories
 * - Module 4: Gaze Attention & Dwell
 * - Module 5: Physical Interaction Yield & Return Rate
 * - Module 6: 4-Stage Conversion Funnel & Behavior Archetypes
 * - Module 7: Spatial Traffic Flow & Heatmaps
 * - Module 8: 5-Pillar Bayesian Product Attractiveness Scoring
 * - Module 9: Prescriptive Merchandising Actions & What-If Simulation
 */

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getDashboardStats,
  getDashboardAnalytics,
  getStores,
  getSyncCachedData,
} from "../services/storeService";

import ExecutivePulseCards from "../components/dashboard/ExecutivePulseCards";
import ConversionFunnelWidget from "../components/dashboard/ConversionFunnelWidget";
import AttractivenessLeaderboardWidget from "../components/dashboard/AttractivenessLeaderboardWidget";
import ShopperArchetypesWidget from "../components/dashboard/ShopperArchetypesWidget";
import PrescriptiveActionFeed from "../components/dashboard/PrescriptiveActionFeed";
import PlanogramSwapSimulator from "../components/recommendations/PlanogramSwapSimulator";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [selectedStoreId, setSelectedStoreId] = useState("");
  const [storesList, setStoresList] = useState([]);

  const cachedStats = getSyncCachedData("dashboard", "stats")?.data;
  const cachedAnalytics = getSyncCachedData("dashboard", "analytics_global")?.data;

  const [stats, setStats] = useState(cachedStats || null);
  const [analytics, setAnalytics] = useState(cachedAnalytics || null);
  const [loading, setLoading] = useState(!cachedStats && !cachedAnalytics);
  const [refreshing, setRefreshing] = useState(false);

  // Simulator Modal State
  const [simulatorOpen, setSimulatorOpen] = useState(false);
  const [selectedProductForSim, setSelectedProductForSim] = useState(null);

  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role || "Administrator";

  const loadData = (storeId = selectedStoreId, force = false) => {
    if (force) setRefreshing(true);
    else if (!stats && !analytics) setLoading(true);

    Promise.allSettled([
      getDashboardStats(force),
      getDashboardAnalytics(storeId || null, force),
      getStores(),
    ])
      .then(([statsRes, analyticsRes, storesRes]) => {
        if (statsRes.status === "fulfilled" && statsRes.value?.data) {
          const statsData = statsRes.value.data.data || statsRes.value.data;
          setStats(statsData);
        }
        if (analyticsRes.status === "fulfilled" && analyticsRes.value?.data) {
          const analyticsData = analyticsRes.value.data.data || analyticsRes.value.data;
          setAnalytics(analyticsData);
        }
        if (storesRes.status === "fulfilled" && storesRes.value?.data) {
          const storesData = Array.isArray(storesRes.value.data)
            ? storesRes.value.data
            : storesRes.value.data?.data || [];
          setStoresList(storesData);
        }
      })
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadData(selectedStoreId);
  }, [selectedStoreId]);

  const handleStoreChange = (e) => {
    setSelectedStoreId(e.target.value);
  };

  const handleOpenSimulator = (rec = null) => {
    if (rec?.target_id) {
      setSelectedProductForSim({
        product_id: rec.target_id,
        product_name: rec.target_name,
        category: "General",
        intrinsic_attractiveness_score: rec.current_metrics?.intrinsic_attractiveness || 70.0,
        attractiveness_score: rec.current_metrics?.observed_attractiveness || 50.0,
        shelf_visibility: {
          shelf_tier: rec.shelf_swap_details?.from_tier || "BOTTOM",
          gamma_coefficient: rec.shelf_swap_details?.from_gamma || 0.40,
        },
      });
    } else {
      setSelectedProductForSim(null);
    }
    setSimulatorOpen(true);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const roleConfigs = {
    Administrator: {
      gradient: "from-violet-500 to-indigo-600",
      badge: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    },
    "Store Manager": {
      gradient: "from-emerald-500 to-teal-600",
      badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    },
    "Retail Analyst": {
      gradient: "from-amber-500 to-orange-600",
      badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    },
    "Marketing Manager": {
      gradient: "from-pink-500 to-rose-600",
      badge: "bg-pink-500/10 text-pink-400 border-pink-500/20",
    },
  };

  const currentRole = roleConfigs[userRole] || roleConfigs.Administrator;

  const entityCounters = [
    { label: "Stores", count: stats?.stores ?? 0, path: "/stores", color: "text-violet-400" },
    { label: "Zones", count: stats?.zones ?? 0, path: "/zones", color: "text-emerald-400" },
    { label: "Shelves", count: stats?.shelves ?? 0, path: "/shelves", color: "text-amber-400" },
    { label: "Products", count: stats?.products ?? 0, path: "/products", color: "text-pink-400" },
    { label: "Cameras", count: stats?.cameras ?? 0, path: "/cameras", color: "text-cyan-400" },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-fade-in pb-16">
      {/* ── Top Header & Fleet Filter Bar ────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {getGreeting()}, {user?.full_name?.split(" ")[0] || "Executive"} 👋
            </h1>
            <span className={`hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-semibold border ${currentRole.badge}`}>
              {userRole}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Retail Intelligence Command Center • Multi-Camera Computer Vision & Attention Scoring
          </p>
        </div>

        {/* Action Controls & Store Selector */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Store Selector */}
          <div className="relative">
            <select
              value={selectedStoreId}
              onChange={handleStoreChange}
              className="appearance-none bg-gray-800/90 hover:bg-gray-800 border border-gray-700/80 text-white text-xs rounded-xl pl-3.5 pr-8 py-2 font-medium focus:outline-none focus:border-violet-500 transition-colors shadow-inner"
            >
              <option value="">🏬 All Store Fleet (Global)</option>
              {storesList.map((s) => (
                <option key={s.id} value={s.id}>
                  🏬 {s.name}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-gray-400">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          {/* Quick Refresh */}
          <button
            onClick={() => loadData(selectedStoreId, true)}
            disabled={refreshing}
            className="p-2 bg-gray-800/90 hover:bg-gray-700/80 border border-gray-700/80 rounded-xl text-gray-300 hover:text-white transition-colors"
            title="Refresh Intelligence Data"
          >
            <svg
              className={`w-4 h-4 ${refreshing ? "animate-spin text-violet-400" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

          {/* What-If Simulator Quick Button */}
          <button
            onClick={() => handleOpenSimulator()}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-violet-600/20 transition-all hover:scale-[1.02]"
          >
            <span>🔮</span>
            <span>What-If Studio</span>
          </button>
        </div>
      </div>

      {/* ── Entity Quick Counters Strip ──────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {entityCounters.map((ec) => (
          <button
            key={ec.label}
            onClick={() => navigate(ec.path)}
            className="bg-gray-900/40 hover:bg-gray-800/60 border border-gray-800/80 rounded-xl p-3 flex items-center justify-between text-left transition-colors group"
          >
            <div>
              <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">
                {ec.label}
              </p>
              <p className="text-xl font-extrabold text-white font-mono mt-0.5">
                {ec.count}
              </p>
            </div>
            <span className={`text-xs font-semibold ${ec.color} opacity-80 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all`}>
              →
            </span>
          </button>
        ))}
      </div>

      {/* ── Executive Pulse 5 KPI Cards ──────────────────────────────── */}
      <ExecutivePulseCards kpis={analytics?.kpis} loading={loading} />

      {/* ── Primary Intelligence Grid: Funnel & Recommendations ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ConversionFunnelWidget
          funnel={analytics?.funnel}
          loading={loading}
          onNavigateJobs={() => navigate("/ai-jobs")}
        />
        <PrescriptiveActionFeed
          recommendations={analytics?.recommendations}
          loading={loading}
          onOpenSimulator={handleOpenSimulator}
          onNavigateRecommendations={() => navigate("/recommendations")}
        />
      </div>

      {/* ── Secondary Intelligence Grid: Attractiveness & Archetypes ──── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AttractivenessLeaderboardWidget
          leaderboard={analytics?.leaderboard}
          loading={loading}
          onNavigateScoring={() => navigate("/analytics")}
        />
        <ShopperArchetypesWidget
          archetypes={analytics?.archetypes}
          loading={loading}
          onNavigateBehavior={() => navigate("/analytics")}
        />
      </div>

      {/* ── Recent AI Processing Pipelines Table ─────────────────────── */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>📹</span> Live Video Analytics Jobs Pipeline
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Recent vision pipelines tracking multi-camera shopper attention
            </p>
          </div>
          <button
            onClick={() => navigate("/ai-jobs")}
            className="text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors"
          >
            Manage Jobs →
          </button>
        </div>

        {analytics?.recent_jobs && analytics.recent_jobs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="pb-3 font-semibold">Camera Source</th>
                  <th className="pb-3 font-semibold">Store</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Execution Time</th>
                  <th className="pb-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {analytics.recent_jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 font-semibold text-white">
                      {job.camera_name || "Camera"}
                    </td>
                    <td className="py-3 text-gray-400">{job.store_name}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          job.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : job.status === "PROCESSING"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse"
                            : job.status === "FAILED"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-gray-500/10 text-gray-400"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-gray-400">
                      {job.duration ? `${job.duration}s` : "—"}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => navigate("/ai-jobs")}
                        className="text-violet-400 hover:text-violet-300 font-semibold"
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500 text-xs">
            No recent video jobs found. Launch an AI Job to stream attention telemetry.
          </div>
        )}
      </div>

      {/* ── Modal: What-If Planogram Simulator ──────────────────────── */}
      {simulatorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-gray-900 border border-gray-800 rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative">
            <button
              onClick={() => setSimulatorOpen(false)}
              className="absolute top-5 right-5 p-2 rounded-xl bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <PlanogramSwapSimulator initialProduct={selectedProductForSim} />
          </div>
        </div>
      )}
    </div>
  );
}
