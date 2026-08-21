/**
 * Module 5 — Product Interaction Analysis UI Component
 * =======================================================
 * Displays comprehensive product and shelf interaction analytics:
 * - Interaction Overview & KPI Cards (Views, Viewers, Pickups, Returns, Comparisons, Purchases)
 * - Product Engagement Matrix (Views, Duration, Pickups, Returns, Comparisons, Repeat Interactions)
 * - Shelf Interaction Monitoring (Visits vs Attention vs Interactions vs Pickups/Returns)
 * - Multi-Product Comparison & Consideration Journeys
 * - Granular Interaction Events Log with Filtering & Search
 * - Structured Markdown & JSON Report Viewer
 */

import { useState, useEffect, useCallback } from "react";
import {
  getModule5Analysis,
  getModule5Events,
  getModule5Report,
  runModule5Job,
} from "../../services/storeService";

function EventTypeBadge({ type }) {
  const map = {
    PRODUCT_VIEWED: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    PRODUCT_PICKED_UP: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    PRODUCT_RETURNED: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    PRODUCT_PURCHASED: "bg-purple-500/10 text-purple-300 border-purple-500/20",
    PRODUCT_COMPARED: "bg-violet-500/10 text-violet-300 border-violet-500/20",
  };

  const icons = {
    PRODUCT_VIEWED: "👁️",
    PRODUCT_PICKED_UP: "🖐️",
    PRODUCT_RETURNED: "🔄",
    PRODUCT_PURCHASED: "💳",
    PRODUCT_COMPARED: "⚖️",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium border ${
        map[type] || "bg-gray-500/10 text-gray-400 border-gray-500/20"
      }`}
    >
      <span>{icons[type] || "📌"}</span>
      <span>{type?.replace("PRODUCT_", "") || type}</span>
    </span>
  );
}

function MetricCard({ label, value, icon, gradient, subtitle, badge }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-gray-700/60 transition-all">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-lg opacity-90`}
        >
          {icon}
        </div>
      </div>
      <div>
        <div className="flex items-baseline gap-2">
          <p className="text-2xl font-bold text-white tracking-tight">{value ?? "—"}</p>
          {badge && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">
              {badge}
            </span>
          )}
        </div>
        {subtitle && <p className="text-[11px] text-gray-400 mt-1">{subtitle}</p>}
      </div>
    </div>
  );
}

export default function Module5ProductInteraction({ jobId, job }) {
  const [activeSubTab, setActiveSubTab] = useState("overview"); // overview | products | shelves | events | comparisons | report
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Events state
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventFilter, setEventFilter] = useState({
    eventType: "",
    search: "",
    trackId: "",
  });

  // Report state
  const [markdownReport, setMarkdownReport] = useState("");
  const [reportLoading, setReportLoading] = useState(false);

  // Search in products table
  const [productSearch, setProductSearch] = useState("");

  const fetchData = useCallback(async () => {
    if (!jobId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getModule5Analysis(jobId);
      setData(res.data);
    } catch (err) {
      console.error("Error fetching Module 5 analysis:", err);
      setError(err.response?.data?.detail || "Failed to load Product Interaction Analysis.");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load events when tab switches
  const fetchEvents = useCallback(async () => {
    if (!jobId) return;
    try {
      setEventsLoading(true);
      const params = {};
      if (eventFilter.eventType) params.event_type = eventFilter.eventType;
      if (eventFilter.trackId) params.track_id = parseInt(eventFilter.trackId, 10);
      const res = await getModule5Events(jobId, params);
      setEvents(res.data || []);
    } catch (err) {
      console.error("Error loading Module 5 events:", err);
    } finally {
      setEventsLoading(false);
    }
  }, [jobId, eventFilter]);

  useEffect(() => {
    if (activeSubTab === "events") {
      fetchEvents();
    }
  }, [activeSubTab, fetchEvents]);

  // Load report when report tab active
  const fetchReport = useCallback(async () => {
    if (!jobId) return;
    try {
      setReportLoading(true);
      const res = await getModule5Report(jobId);
      setMarkdownReport(res.data?.markdown_report || "");
    } catch (err) {
      console.error("Error fetching Module 5 report:", err);
    } finally {
      setReportLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (activeSubTab === "report") {
      fetchReport();
    }
  }, [activeSubTab, fetchReport]);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const res = await runModule5Job(jobId);
      setData(res.data);
      if (activeSubTab === "events") fetchEvents();
      if (activeSubTab === "report") fetchReport();
    } catch (err) {
      console.error("Error refreshing Module 5 analysis:", err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="py-16 text-center">
        <div className="w-9 h-9 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-400 font-medium">
          Loading Module 5 Product Interaction Analysis...
        </p>
        <p className="text-xs text-gray-600 mt-1">
          Ingesting Module 3 & Module 4 spatial and attention tracking data
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-center my-4">
        <svg
          className="w-10 h-10 text-red-400 mx-auto mb-2"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <p className="text-sm font-semibold text-red-300 mb-1">Module 5 Analysis Error</p>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white transition-all shadow-lg"
        >
          {refreshing ? "Computing..." : "Run Product Interaction Analysis"}
        </button>
      </div>
    );
  }

  const summary = data?.summary || {};
  const products = data?.products || [];
  const shelves = data?.shelves || [];
  const comparisons = data?.comparisons || [];

  const filteredProducts = products.filter((p) => {
    if (!productSearch) return true;
    const q = productSearch.toLowerCase();
    return (
      p.product_name?.toLowerCase().includes(q) ||
      p.sku?.toLowerCase().includes(q) ||
      p.shelf_name?.toLowerCase().includes(q)
    );
  });

  const filteredEvents = events.filter((e) => {
    if (!eventFilter.search) return true;
    const q = eventFilter.search.toLowerCase();
    return (
      e.product_name?.toLowerCase().includes(q) ||
      e.shelf_name?.toLowerCase().includes(q) ||
      e.event_id?.toLowerCase().includes(q) ||
      String(e.track_id).includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* ── Sub-navigation Header ──────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800/80 pb-4">
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
          {[
            { id: "overview", label: "Overview", icon: "📊" },
            { id: "products", label: `Product Engagement (${products.length})`, icon: "📦" },
            { id: "shelves", label: `Shelf Interaction (${shelves.length})`, icon: "🗄️" },
            { id: "comparisons", label: `Comparisons (${comparisons.length})`, icon: "⚖️" },
            { id: "events", label: "Interaction Events", icon: "⚡" },
            { id: "report", label: "Report View", icon: "📄" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all whitespace-nowrap ${
                activeSubTab === tab.id
                  ? "bg-violet-600/90 text-white shadow-lg shadow-violet-600/20 border border-violet-500/30"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/50"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-gray-300 bg-gray-800/60 hover:bg-gray-800 hover:text-white border border-gray-700/50 transition-all flex items-center gap-1.5 self-start sm:self-auto disabled:opacity-50"
        >
          <svg
            className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-violet-400" : ""}`}
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
          {refreshing ? "Refreshing..." : "Re-evaluate"}
        </button>
      </div>

      {/* ── TAB 1: OVERVIEW ────────────────────────────────── */}
      {activeSubTab === "overview" && (
        <div className="space-y-6 animate-fadeIn">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
            <MetricCard
              label="Product Views"
              value={summary.total_views}
              subtitle="Total viewed events"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              }
              gradient="from-cyan-500 to-blue-600"
            />
            <MetricCard
              label="Unique Viewers"
              value={summary.total_unique_viewers}
              subtitle="Unique shoppers"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              }
              gradient="from-blue-500 to-indigo-600"
            />
            <MetricCard
              label="Avg View Duration"
              value={`${summary.average_view_duration_sec?.toFixed(2)}s`}
              subtitle={`Total: ${summary.total_view_duration_sec?.toFixed(1)}s`}
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
              gradient="from-indigo-500 to-purple-600"
            />
            <MetricCard
              label="Product Pickups"
              value={summary.total_pickups}
              subtitle={summary.pickup_detection_status?.includes("INSUFFICIENT") ? "Visual evidence gated" : "Verified"}
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
                </svg>
              }
              gradient="from-emerald-500 to-teal-600"
            />
            <MetricCard
              label="Comparisons"
              value={summary.total_comparisons}
              subtitle="Multi-item sessions"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                </svg>
              }
              gradient="from-violet-500 to-fuchsia-600"
            />
            <MetricCard
              label="Purchases"
              value={summary.total_purchases}
              subtitle="POS transaction data"
              badge="POS Only"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              }
              gradient="from-amber-500 to-orange-600"
            />
          </div>

          {/* Status & Technical Disclaimers Banner */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-gray-900/40 border border-gray-800/60 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Interaction Pipeline Status
                  </h4>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Module 5 executes natively on Module 3 tracking trajectories, sessions, and Module 4 head-pose attention vectors without re-running heavy neural networks.
                </p>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-800/60 flex flex-wrap gap-2 text-[11px]">
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
                  Deduplication: Active
                </span>
                <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono">
                  Multi-Person ByteTrack: Isolated
                </span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-gray-900/40 border border-gray-800/60 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Evidence Verification Gating
                  </h4>
                </div>
                <ul className="text-xs text-gray-400 space-y-1">
                  <li>
                    <strong className="text-gray-300">Pickups:</strong>{" "}
                    {summary.pickup_detection_status}
                  </li>
                  <li>
                    <strong className="text-gray-300">Purchases:</strong>{" "}
                    {summary.purchase_data_status}
                  </li>
                </ul>
              </div>
              <p className="mt-2 text-[11px] text-gray-500 italic">
                *No fictitious pickup or checkout transactions are fabricated without direct sensory evidence.
              </p>
            </div>
          </div>

          {/* Quick Shelf Engagement Preview */}
          <div className="bg-gray-900/40 border border-gray-800/60 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Shelf Activity Breakdown
              </h4>
              <button
                onClick={() => setActiveSubTab("shelves")}
                className="text-xs text-violet-400 hover:text-violet-300 font-medium"
              >
                View Details &rarr;
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {shelves.map((s) => (
                <div
                  key={s.shelf_id}
                  className="p-3.5 rounded-xl bg-gray-800/30 border border-gray-800/80 hover:border-gray-700/80 transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-white">{s.shelf_name}</p>
                    <span className="text-[10px] font-mono text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded">
                      {s.shelf_code || s.shelf_id}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs mt-3 pt-2 border-t border-gray-800/60">
                    <div>
                      <p className="text-gray-500 text-[10px]">Visits</p>
                      <p className="font-bold text-gray-200 mt-0.5">{s.shelf_visits}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-[10px]">Viewers</p>
                      <p className="font-bold text-cyan-300 mt-0.5">{s.shelf_viewers}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-[10px]">Attention</p>
                      <p className="font-bold text-violet-300 mt-0.5">
                        {s.shelf_attention_duration_sec?.toFixed(1)}s
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: PRODUCT ENGAGEMENT ──────────────────────── */}
      {activeSubTab === "products" && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Product Engagement Matrix</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Evaluated viewer counts, sustained attention duration, and comparison patterns per product
              </p>
            </div>
            <div className="w-full sm:w-64">
              <input
                type="text"
                placeholder="Search products or SKUs..."
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                className="w-full px-3 py-1.5 rounded-xl bg-gray-900/80 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500"
              />
            </div>
          </div>

          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 font-medium bg-gray-900/40">
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-3">SKU</th>
                    <th className="py-3 px-3">Shelf</th>
                    <th className="py-3 px-3 text-center">Views</th>
                    <th className="py-3 px-3 text-center">Unique Viewers</th>
                    <th className="py-3 px-3 text-center">Total Duration</th>
                    <th className="py-3 px-3 text-center">Avg Duration</th>
                    <th className="py-3 px-3 text-center">Pickups</th>
                    <th className="py-3 px-3 text-center">Comparisons</th>
                    <th className="py-3 px-3 text-center">Repeat Views</th>
                    <th className="py-3 px-4 text-right">Mapping Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {filteredProducts.length === 0 ? (
                    <tr>
                      <td colSpan="11" className="py-8 text-center text-gray-500">
                        No product engagement records found.
                      </td>
                    </tr>
                  ) : (
                    filteredProducts.map((p) => (
                      <tr key={p.product_id} className="hover:bg-gray-800/20 transition-all">
                        <td className="py-3.5 px-4 font-semibold text-white">
                          {p.product_name}
                        </td>
                        <td className="py-3.5 px-3 font-mono text-gray-400 text-[11px]">
                          {p.sku || "N/A"}
                        </td>
                        <td className="py-3.5 px-3 text-gray-300">
                          {p.shelf_name || "Unassigned"}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-cyan-300">
                          {p.views}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-gray-200">
                          {p.unique_viewers}
                        </td>
                        <td className="py-3.5 px-3 text-center text-gray-200 font-mono">
                          {p.total_view_duration_sec?.toFixed(1)}s
                        </td>
                        <td className="py-3.5 px-3 text-center text-gray-300 font-mono">
                          {p.average_view_duration_sec?.toFixed(1)}s
                        </td>
                        <td className="py-3.5 px-3 text-center text-gray-400">
                          {p.pickup_events}
                        </td>
                        <td className="py-3.5 px-3 text-center text-violet-300 font-medium">
                          {p.comparison_events}
                        </td>
                        <td className="py-3.5 px-3 text-center text-amber-300">
                          {p.repeat_interactions}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${
                              p.is_spatial_mapped
                                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                                : "bg-blue-500/10 text-blue-300 border-blue-500/20"
                            }`}
                          >
                            {p.status_note}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: SHELF INTERACTION MONITORING ────────────── */}
      {activeSubTab === "shelves" && (
        <div className="space-y-4 animate-fadeIn">
          <div>
            <h3 className="text-sm font-semibold text-white">Shelf Interaction Monitoring</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Strict distinction between Zone Visits, Shelf Gaze Attention, and Sustained Interactions
            </p>
          </div>

          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 font-medium bg-gray-900/40">
                    <th className="py-3 px-4">Shelf Name</th>
                    <th className="py-3 px-3">Code</th>
                    <th className="py-3 px-3">Zone</th>
                    <th className="py-3 px-3 text-center">Shelf Visits</th>
                    <th className="py-3 px-3 text-center">Shelf Viewers</th>
                    <th className="py-3 px-3 text-center">Attention Events</th>
                    <th className="py-3 px-3 text-center">Attention Duration</th>
                    <th className="py-3 px-3 text-center">Product Views</th>
                    <th className="py-3 px-3 text-center">Sustained Interactions</th>
                    <th className="py-3 px-3 text-center">Pickups</th>
                    <th className="py-3 px-4 text-right">Engagement Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {shelves.length === 0 ? (
                    <tr>
                      <td colSpan="11" className="py-8 text-center text-gray-500">
                        No shelves configured for this store/camera.
                      </td>
                    </tr>
                  ) : (
                    shelves.map((s) => (
                      <tr key={s.shelf_id} className="hover:bg-gray-800/20 transition-all">
                        <td className="py-3.5 px-4 font-semibold text-white">
                          {s.shelf_name}
                        </td>
                        <td className="py-3.5 px-3 font-mono text-gray-400 text-[11px]">
                          {s.shelf_code || s.shelf_id}
                        </td>
                        <td className="py-3.5 px-3 text-gray-300">
                          {s.zone_id || "unknown"}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-gray-300">
                          {s.shelf_visits}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-cyan-300">
                          {s.shelf_viewers}
                        </td>
                        <td className="py-3.5 px-3 text-center text-gray-200">
                          {s.shelf_attention_events}
                        </td>
                        <td className="py-3.5 px-3 text-center font-mono text-gray-200">
                          {s.shelf_attention_duration_sec?.toFixed(1)}s
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-violet-300">
                          {s.product_views}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-indigo-300">
                          {s.shelf_interactions}
                        </td>
                        <td className="py-3.5 px-3 text-center text-gray-400">
                          {s.pickup_events}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-emerald-400">
                          {s.total_engagement_duration_sec?.toFixed(1)}s
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 4: COMPARISON PATTERNS ─────────────────────── */}
      {activeSubTab === "comparisons" && (
        <div className="space-y-4 animate-fadeIn">
          <div>
            <h3 className="text-sm font-semibold text-white">
              Observed Multi-Product Comparison Patterns
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Shoppers who attended to or interacted with multiple distinct products within the same shopping session
            </p>
          </div>

          {comparisons.length === 0 ? (
            <div className="py-12 text-center bg-gray-900/40 border border-gray-800/60 rounded-2xl p-6">
              <span className="text-3xl mb-2 inline-block">⚖️</span>
              <p className="text-sm font-semibold text-gray-300">
                No Multi-Product Comparisons Observed
              </p>
              <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
                No single shopper session exhibited sequential viewing or interaction across 2 or more distinct products/shelves in this video.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {comparisons.map((c) => (
                <div
                  key={c.pattern_id}
                  className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5 hover:border-violet-500/30 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-gray-800/60">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold bg-violet-500/10 text-violet-300 border border-violet-500/20">
                        {c.pattern_id}
                      </span>
                      <span className="text-xs text-gray-400">
                        Shopper <strong>Track #{c.track_id}</strong>
                        {c.session_id ? ` (Session: ${c.session_id})` : ""}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400 font-mono">
                      <span>Span: {c.start_time?.toFixed(1)}s - {c.end_time?.toFixed(1)}s</span>
                      <span className="text-emerald-400 font-bold">
                        Total: {c.total_duration_sec?.toFixed(1)}s
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-gray-300 mb-3 font-medium">
                    {c.pattern_description}
                  </p>

                  <div className="bg-gray-950/50 rounded-xl p-3 border border-gray-800/60">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-2">
                      Sequential Consideration Timeline
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      {c.interaction_sequence?.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-xs">
                            <span className="font-semibold text-white">
                              {step.product_name}
                            </span>
                            <span className="text-[10px] text-gray-400 ml-1.5 font-mono">
                              ({step.duration_seconds}s)
                            </span>
                          </div>
                          {idx < c.interaction_sequence.length - 1 && (
                            <span className="text-violet-400 text-xs">&rarr;</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 5: INTERACTION EVENTS LOG ─────────────────── */}
      {activeSubTab === "events" && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Granular Interaction Events</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Deduplicated chronological stream of product views, pickups, returns, and comparisons
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={eventFilter.eventType}
                onChange={(e) =>
                  setEventFilter((prev) => ({ ...prev, eventType: e.target.value }))
                }
                className="px-3 py-1.5 rounded-xl bg-gray-900 border border-gray-800 text-xs text-white focus:outline-none"
              >
                <option value="">All Event Types</option>
                <option value="PRODUCT_VIEWED">Product Viewed</option>
                <option value="PRODUCT_PICKED_UP">Product Picked Up</option>
                <option value="PRODUCT_RETURNED">Product Returned</option>
                <option value="PRODUCT_COMPARED">Product Compared</option>
                <option value="PRODUCT_PURCHASED">Product Purchased</option>
              </select>

              <input
                type="text"
                placeholder="Filter by Track ID..."
                value={eventFilter.trackId}
                onChange={(e) =>
                  setEventFilter((prev) => ({ ...prev, trackId: e.target.value }))
                }
                className="w-32 px-3 py-1.5 rounded-xl bg-gray-900 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none"
              />

              <input
                type="text"
                placeholder="Search..."
                value={eventFilter.search}
                onChange={(e) =>
                  setEventFilter((prev) => ({ ...prev, search: e.target.value }))
                }
                className="w-36 px-3 py-1.5 rounded-xl bg-gray-900 border border-gray-800 text-xs text-white placeholder-gray-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            {eventsLoading ? (
              <div className="py-12 text-center">
                <div className="w-6 h-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-gray-500">Loading events...</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400 font-medium bg-gray-900/40">
                      <th className="py-3 px-4">Event ID</th>
                      <th className="py-3 px-3">Event Type</th>
                      <th className="py-3 px-3">Track ID</th>
                      <th className="py-3 px-3">Product</th>
                      <th className="py-3 px-3">Shelf</th>
                      <th className="py-3 px-3 text-center">Start Time</th>
                      <th className="py-3 px-3 text-center">End Time</th>
                      <th className="py-3 px-3 text-center">Duration</th>
                      <th className="py-3 px-3 text-center">Confidence</th>
                      <th className="py-3 px-4 text-right">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60">
                    {filteredEvents.length === 0 ? (
                      <tr>
                        <td colSpan="10" className="py-8 text-center text-gray-500">
                          No matching interaction events found.
                        </td>
                      </tr>
                    ) : (
                      filteredEvents.map((ev) => (
                        <tr key={ev.event_id} className="hover:bg-gray-800/20 transition-all">
                          <td className="py-3 px-4 font-mono text-[11px] text-gray-400">
                            {ev.event_id}
                          </td>
                          <td className="py-3 px-3">
                            <EventTypeBadge type={ev.event_type} />
                          </td>
                          <td className="py-3 px-3 font-semibold text-white">
                            #{ev.track_id}
                          </td>
                          <td className="py-3 px-3 text-gray-200">
                            {ev.product_name || "N/A"}
                          </td>
                          <td className="py-3 px-3 text-gray-300">
                            {ev.shelf_name || "N/A"}
                          </td>
                          <td className="py-3 px-3 text-center font-mono text-gray-300">
                            {ev.start_time?.toFixed(2)}s
                          </td>
                          <td className="py-3 px-3 text-center font-mono text-gray-400">
                            {ev.end_time ? `${ev.end_time?.toFixed(2)}s` : "—"}
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-semibold text-cyan-300">
                            {ev.duration_seconds?.toFixed(2)}s
                          </td>
                          <td className="py-3 px-3 text-center font-mono text-gray-400">
                            {ev.confidence?.toFixed(2)}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-[10px] text-gray-500">
                            {ev.source}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 6: REPORT VIEW ─────────────────────────────── */}
      {activeSubTab === "report" && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Structured Markdown & JSON Report
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Export-ready summary document for Module 5
              </p>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(markdownReport);
                alert("Markdown report copied to clipboard!");
              }}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 transition-all flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              Copy Markdown
            </button>
          </div>

          <div className="bg-gray-950/80 border border-gray-800 rounded-2xl p-6 font-mono text-xs text-gray-300 whitespace-pre-wrap max-h-[600px] overflow-y-auto leading-relaxed scrollbar-thin scrollbar-thumb-gray-800">
            {reportLoading ? (
              <div className="py-12 text-center text-gray-500 font-sans">
                Loading report content...
              </div>
            ) : (
              markdownReport || "No report generated yet."
            )}
          </div>
        </div>
      )}
    </div>
  );
}
