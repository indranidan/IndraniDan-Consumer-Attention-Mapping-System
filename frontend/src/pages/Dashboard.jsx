/**
 * Dashboard Page
 * ===============
 * Management dashboard showing real entity counts and quick navigation.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getDashboardStats } from "../services/storeService";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role;

  useEffect(() => {
    getDashboardStats()
      .then((res) => setStats(res.data))
      .catch(() => setStats({ stores: 0, zones: 0, shelves: 0, products: 0, cameras: 0 }))
      .finally(() => setLoading(false));
  }, []);

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  // Role-based accent colors
  const roleColors = {
    Administrator: { bg: "from-violet-500 to-indigo-600", badge: "bg-violet-500/10 text-violet-400 border-violet-500/20" },
    "Store Manager": { bg: "from-emerald-500 to-teal-600", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
    "Retail Analyst": { bg: "from-amber-500 to-orange-600", badge: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
    "Marketing Manager": { bg: "from-pink-500 to-rose-600", badge: "bg-pink-500/10 text-pink-400 border-pink-500/20" },
  };

  const colors = roleColors[userRole] || roleColors.Administrator;

  const statCards = [
    {
      label: "Stores",
      value: stats?.stores ?? 0,
      path: "/stores",
      gradient: "from-violet-500 to-indigo-600",
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
          />
        </svg>
      ),
    },
    {
      label: "Zones",
      value: stats?.zones ?? 0,
      path: "/zones",
      gradient: "from-emerald-500 to-teal-600",
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
          />
        </svg>
      ),
    },
    {
      label: "Shelves",
      value: stats?.shelves ?? 0,
      path: "/shelves",
      gradient: "from-amber-500 to-orange-600",
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      ),
    },
  ];

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">
          {getGreeting()}, {user?.full_name?.split(" ")[0] || "User"} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Welcome to the Consumer Attention Mapping System
        </p>
      </div>

      {/* Role Badge */}
      <div className="flex items-center gap-3 mb-8">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${colors.bg} flex items-center justify-center text-white shadow-lg shadow-violet-500/10`}>
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
        </div>
        <div>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium border ${colors.badge}`}>
            {userRole}
          </span>
          <p className="text-xs text-gray-500 mt-0.5">Your current role</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {statCards.map((card) => (
          <button
            key={card.label}
            onClick={() => navigate(card.path)}
            className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5 hover:border-gray-700/50 transition-all duration-300 group text-left"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">{card.label}</span>
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white shadow-lg opacity-80 group-hover:opacity-100 transition-opacity`}>
                {card.icon}
              </div>
            </div>
            {loading ? (
              <div className="h-7 w-12 bg-gray-800/50 rounded-lg animate-pulse" />
            ) : (
              <p className="text-2xl font-bold text-white">{card.value}</p>
            )}
          </button>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800/30 rounded-2xl p-6">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white mb-1">Store Management</h4>
            <p className="text-sm text-gray-500">
              Use the sidebar to navigate between Stores, Zones, Shelves, Products, and Cameras.
              Start by creating a store, then build out its structure with zones and shelves.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
