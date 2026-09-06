/**
 * Dashboard – Role-Specific Orchestrator (Module 10)
 * ===================================================
 * Detects the authenticated user's role and renders the corresponding
 * minimalist dashboard view. Administrators get a RoleSwitcher pill bar
 * to preview any role's perspective.
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

import RoleSwitcher from "../components/dashboard/RoleSwitcher";
import StoreManagerDashboard from "../components/dashboard/StoreManagerDashboard";
import RetailAnalystDashboard from "../components/dashboard/RetailAnalystDashboard";
import MarketingDashboard from "../components/dashboard/MarketingDashboard";
import AdminDashboard from "../components/dashboard/AdminDashboard";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  /* ── Determine the user's actual role ─────────────────────── */
  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role || "Administrator";

  /* ── Active view role (switchable by Admins) ──────────────── */
  const [activeRole, setActiveRole] = useState(userRole);
  const isAdmin = userRole === "Administrator";

  /* ── Store filter ─────────────────────────────────────────── */
  const [selectedStoreId, setSelectedStoreId] = useState("");
  const [storesList, setStoresList] = useState([]);

  /* ── Data state ───────────────────────────────────────────── */
  const cachedStats = getSyncCachedData("dashboard", "stats")?.data;
  const cachedAnalytics = getSyncCachedData("dashboard", "analytics_global")?.data;

  const [stats, setStats] = useState(cachedStats || null);
  const [analytics, setAnalytics] = useState(cachedAnalytics || null);
  const [loading, setLoading] = useState(!cachedStats && !cachedAnalytics);
  const [refreshing, setRefreshing] = useState(false);

  /* ── Data loader ──────────────────────────────────────────── */
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
          const d = statsRes.value.data.data || statsRes.value.data;
          setStats(d);
        }
        if (analyticsRes.status === "fulfilled" && analyticsRes.value?.data) {
          const d = analyticsRes.value.data.data || analyticsRes.value.data;
          setAnalytics(d);
        }
        if (storesRes.status === "fulfilled" && storesRes.value?.data) {
          const d = Array.isArray(storesRes.value.data)
            ? storesRes.value.data
            : storesRes.value.data?.data || [];
          setStoresList(d);
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

  /* ── Sync activeRole when userRole changes ────────────────── */
  useEffect(() => {
    if (!isAdmin) setActiveRole(userRole);
  }, [userRole]);

  /* ── Greeting ─────────────────────────────────────────────── */
  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  };

  /* ── Role view labels ─────────────────────────────────────── */
  const roleLabels = {
    "Store Manager": { icon: "🏪", title: "Store Manager Dashboard", gradient: "from-emerald-500 to-teal-600" },
    "Retail Analyst": { icon: "📊", title: "Retail Analyst Dashboard", gradient: "from-amber-500 to-orange-600" },
    "Marketing Manager": { icon: "🎯", title: "Marketing Manager Dashboard", gradient: "from-pink-500 to-rose-600" },
    Administrator: { icon: "⚙️", title: "Administrator Dashboard", gradient: "from-violet-500 to-indigo-600" },
  };

  const currentLabel = roleLabels[activeRole] || roleLabels.Administrator;

  /* ── Render active role's view ────────────────────────────── */
  const renderRoleView = () => {
    switch (activeRole) {
      case "Store Manager":
        return <StoreManagerDashboard analytics={analytics} stats={stats} loading={loading} />;
      case "Retail Analyst":
        return <RetailAnalystDashboard analytics={analytics} loading={loading} />;
      case "Marketing Manager":
        return <MarketingDashboard analytics={analytics} loading={loading} />;
      case "Administrator":
        return <AdminDashboard analytics={analytics} stats={stats} loading={loading} />;
      default:
        return <StoreManagerDashboard analytics={analytics} stats={stats} loading={loading} />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-fade-in pb-16">
      {/* ── Header Bar ──────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {getGreeting()}, {user?.full_name?.split(" ")[0] || "Executive"} 👋
            </h1>
          </div>
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-1.5">
            <span>{currentLabel.icon}</span>
            {currentLabel.title}
            {selectedStoreId ? ` • ${storesList.find((s) => s.id === selectedStoreId)?.name || "Store"}` : " • All Stores Fleet"}
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Store Selector */}
          <div className="relative">
            <select
              value={selectedStoreId}
              onChange={(e) => setSelectedStoreId(e.target.value)}
              className="appearance-none bg-gray-800/90 hover:bg-gray-800 border border-gray-700/80 text-white text-xs rounded-xl pl-3.5 pr-8 py-2 font-medium focus:outline-none focus:border-violet-500 transition-colors shadow-inner"
            >
              <option value="">🏬 All Stores (Global)</option>
              {storesList.map((s) => (
                <option key={s.id} value={s.id}>🏬 {s.name}</option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-gray-400">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          {/* Refresh */}
          <button
            onClick={() => loadData(selectedStoreId, true)}
            disabled={refreshing}
            className="p-2 bg-gray-800/90 hover:bg-gray-700/80 border border-gray-700/80 rounded-xl text-gray-300 hover:text-white transition-colors"
            title="Refresh data"
          >
            <svg className={`w-4 h-4 ${refreshing ? "animate-spin text-violet-400" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Role Switcher (Admin only) ──────────────────────────── */}
      {isAdmin && (
        <RoleSwitcher activeRole={activeRole} onSwitch={setActiveRole} />
      )}

      {/* ── Active Role View ────────────────────────────────────── */}
      {renderRoleView()}
    </div>
  );
}
