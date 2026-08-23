/**
 * Operational Stats Dashboard
 * ===========================
 * Clean, lightweight operational dashboard showing real-time statistics
 * for Stores, Zones, Shelves, Products, and Cameras.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getDashboardStats, getDashboardAnalytics, getSyncCachedData } from "../services/storeService";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const cachedStats = getSyncCachedData("dashboard", "stats")?.data;
  const cachedAnalytics = getSyncCachedData("dashboard", "analytics")?.data;

  const [stats, setStats] = useState(cachedStats || null);
  const [analytics, setAnalytics] = useState(cachedAnalytics || null);
  const [loading, setLoading] = useState(!cachedStats && !cachedAnalytics);

  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role || "Administrator";

  useEffect(() => {
    Promise.allSettled([getDashboardStats(), getDashboardAnalytics()])
      .then(([statsRes, analyticsRes]) => {
        if (statsRes.status === "fulfilled" && statsRes.value?.data) {
          setStats(statsRes.value.data);
        } else if (!stats) {
          setStats({ stores: 0, zones: 0, shelves: 0, products: 0, cameras: 0 });
        }
        if (analyticsRes.status === "fulfilled" && analyticsRes.value?.data) {
          setAnalytics(analyticsRes.value.data);
        }
      })
      .finally(() => setLoading(false));
  }, []);


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

  const statCards = [
    {
      label: "Stores",
      value: stats?.stores ?? 0,
      path: "/stores",
      gradient: "from-violet-500 to-indigo-600",
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
    {
      label: "Zones",
      value: stats?.zones ?? 0,
      path: "/zones",
      gradient: "from-emerald-500 to-teal-600",
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
        </svg>
      ),
    },
    {
      label: "Shelves",
      value: stats?.shelves ?? 0,
      path: "/shelves",
      gradient: "from-amber-500 to-orange-600",
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
        </svg>
      ),
    },
    {
      label: "Products",
      value: stats?.products ?? 0,
      path: "/products",
      gradient: "from-pink-500 to-rose-600",
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      ),
    },
    {
      label: "Cameras",
      value: stats?.cameras ?? 0,
      path: "/cameras",
      gradient: "from-cyan-500 to-blue-600",
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-fade-in pb-12">
      {/* ── Top Header & Role Badge ───────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {getGreeting()}, {user?.full_name?.split(" ")[0] || "User"} 👋
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Consumer Attention Mapping & Retail Operations Overview
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${currentRole.gradient} flex items-center justify-center text-white shadow-lg`}>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-semibold border ${currentRole.badge}`}>
              {userRole}
            </span>
            <p className="text-[11px] text-gray-500 mt-0.5">Active Session</p>
          </div>
        </div>
      </div>

      {/* ── Primary Operational Stat Cards ────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-5">
        {statCards.map((card) => (
          <button
            key={card.label}
            onClick={() => navigate(card.path)}
            className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 sm:p-6 hover:border-gray-700/80 hover:bg-gray-900/80 transition-all duration-300 group text-left shadow-lg shadow-black/20 relative overflow-hidden"
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                {card.label}
              </span>
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white shadow-lg opacity-85 group-hover:opacity-100 group-hover:scale-105 transition-all`}>
                {card.icon}
              </div>
            </div>
            {loading ? (
              <div className="h-9 w-16 bg-gray-800/50 rounded-lg animate-pulse" />
            ) : (
              <div className="flex items-baseline justify-between mt-2">
                <p className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                  {card.value}
                </p>
                <span className="text-xs text-gray-500 group-hover:text-violet-400 font-medium transition-colors">
                  View →
                </span>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* ── Module 6: Consumer Behavior Intelligence Summary ────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dominant Shopper Archetype Highlight */}
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-violet-400 uppercase tracking-wider flex items-center gap-2">
                <span>🧠</span> Dominant Shopper Archetype
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20 font-mono">
                Module 6
              </span>
            </div>
            <p className="text-2xl font-bold text-white tracking-tight mt-1">
              {analytics?.overview?.dominant_segment ? (
                analytics.overview.dominant_segment.replace("_", " ")
              ) : (
                "Explorer Shoppers"
              )}
            </p>
            <p className="text-xs text-gray-400 mt-2 leading-relaxed">
              {analytics?.overview?.dominant_segment === "QUICK_BUYER"
                ? "Fast-moving target seekers with high path efficiency and minimal dwell time. Ensure key products remain accessible near main aisle."
                : analytics?.overview?.dominant_segment === "COMPARISON_SHOPPER"
                ? "Deep evaluators with high gaze alternation rates. Optimize side-by-side shelf comparisons and price tag visibility."
                : analytics?.overview?.dominant_segment === "BRAND_LOYAL"
                ? "Highly concentrated brand focus. Strengthen brand block displays and dedicated end-caps."
                : "Broad store path exploration with high dwell-to-transit ratio. Maximize promotional impulse triggers across exploration routes."}
            </p>
          </div>

          <div className="mt-5 pt-4 border-t border-gray-800/60 flex items-center justify-between text-xs">
            <span className="text-gray-500">AI Job Analyzed Sessions:</span>
            <span className="font-mono text-cyan-400 font-bold">
              {analytics?.overview?.total_shoppers || stats?.stores || 0} Classified
            </span>
          </div>
        </div>

        {/* Segment Distribution Breakdown */}
        <div className="lg:col-span-2 bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>🎭</span> Cross-Store Shopper Segmentation Breakdown
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Aggregated behavior archetypes across completed video analysis pipelines
              </p>
            </div>
            <button
              onClick={() => navigate("/ai-jobs")}
              className="text-xs text-violet-400 hover:text-violet-300 transition-colors font-medium"
            >
              View Jobs →
            </button>
          </div>

          {analytics?.overview?.segment_distribution &&
          Object.keys(analytics.overview.segment_distribution).length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {Object.entries(analytics.overview.segment_distribution).map(([seg, count]) => {
                const total = Object.values(analytics.overview.segment_distribution).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return (
                  <div key={seg} className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-3.5">
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="font-semibold text-white capitalize">{seg.toLowerCase().replace("_", " ")}</span>
                      <span className="font-mono text-violet-400 font-bold">{count} ({pct}%)</span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-violet-600 to-cyan-500 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 py-2">
              {[
                { name: "Explorer", icon: "🧭", pct: "35%", color: "from-blue-600 to-cyan-500" },
                { name: "Quick Buyer", icon: "⚡", pct: "25%", color: "from-amber-500 to-orange-600" },
                { name: "Comparison", icon: "⚖️", pct: "20%", color: "from-purple-600 to-indigo-600" },
                { name: "Impulse", icon: "🎯", pct: "12%", color: "from-rose-500 to-pink-600" },
                { name: "Brand Loyal", icon: "🏷️", pct: "8%", color: "from-emerald-500 to-teal-600" },
              ].map((archetype) => (
                <div key={archetype.name} className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-3 text-center">
                  <span className="text-xl mb-1 block">{archetype.icon}</span>
                  <p className="text-xs font-semibold text-white">{archetype.name}</p>
                  <p className="text-xs font-mono text-gray-400 mt-0.5">{archetype.pct}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
