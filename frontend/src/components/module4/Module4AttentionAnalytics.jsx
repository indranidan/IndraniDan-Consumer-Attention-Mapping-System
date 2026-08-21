/**
 * Module 4 — Attention Analysis UI Component
 * ============================================
 * Displays dedicated Module 4 analytics:
 * - 3D Head Pose & Estimated Viewing Direction Overview
 * - Shelf Engagement Table (Visitors, Viewers, Dwell, Shelf Attention, Score)
 * - Product Focus Table (Configured vs Not Configured)
 * - Granular Attention Events Log with Direction & Confidence
 * - Camera Spatial Attention Heatmap
 * - Technical Limitations & Scientific Disclaimers
 */

import { useState, useEffect, useCallback } from "react";
import {
  getModule4Analysis,
  getModule4Events,
  getModule4Report,
  getModule4Heatmap,
  runModule4Job,
} from "../../services/storeService";
import api from "../../services/api";

function ScoreBadge({ score }) {
  let color = "text-gray-400 bg-gray-500/10 border-gray-500/20";
  if (score >= 70) {
    color = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  } else if (score >= 40) {
    color = "text-amber-400 bg-amber-500/10 border-amber-500/20";
  } else if (score > 0) {
    color = "text-blue-400 bg-blue-500/10 border-blue-500/20";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-semibold border ${color}`}
    >
      {score.toFixed(1)} / 100
    </span>
  );
}

function DirectionBadge({ direction }) {
  const map = {
    LEFT: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
    RIGHT: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    CENTER: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    UP: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    DOWN: "bg-purple-500/10 text-purple-300 border-purple-500/20",
    UNKNOWN: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono border ${map[direction] || map.UNKNOWN
        }`}
    >
      {direction}
    </span>
  );
}

function MetricCard({ label, value, icon, gradient, subtitle }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-lg opacity-80`}
        >
          {icon}
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-white tracking-tight">{value ?? "—"}</p>
        {subtitle && <p className="text-[11px] text-gray-500 mt-1">{subtitle}</p>}
      </div>
    </div>
  );
}

export default function Module4AttentionAnalytics({ jobId, job }) {
  const [activeSubTab, setActiveSubTab] = useState("overview"); // "overview" | "shelves" | "products" | "events" | "heatmap" | "report"
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Events state
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventFilter, setEventFilter] = useState({
    targetType: "",
    direction: "",
    search: "",
  });

  // Report state
  const [markdownReport, setMarkdownReport] = useState("");
  const [jsonReport, setJsonReport] = useState(null);
  const [reportViewMode, setReportViewMode] = useState("markdown"); // "markdown" | "json"
  const [reportLoading, setReportLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Heatmap state
  const [heatmapInfo, setHeatmapInfo] = useState(null);
  const [heatmapBlobUrl, setHeatmapBlobUrl] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);

  const fetchAnalysis = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getModule4Analysis(jobId);
      setData(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to load Module 4 attention analytics."
      );
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const fetchEvents = useCallback(async () => {
    if (!jobId) return;
    setEventsLoading(true);
    try {
      const res = await getModule4Events(jobId, {
        target_type: eventFilter.targetType || undefined,
        page_size: 100,
      });
      setEvents(res.data || []);
    } catch {
      setEvents([]);
    } finally {
      setEventsLoading(false);
    }
  }, [jobId, eventFilter.targetType]);

  const fetchReport = useCallback(async () => {
    if (!jobId) return;
    setReportLoading(true);
    try {
      const res = await getModule4Report(jobId);
      setMarkdownReport(res.data?.markdown_report || "");
      setJsonReport(res.data?.json_report || null);
    } catch {
      setMarkdownReport("");
    } finally {
      setReportLoading(false);
    }
  }, [jobId]);


  const fetchHeatmap = useCallback(async () => {
    if (!jobId) return;
    setHeatmapLoading(true);
    try {
      const res = await getModule4Heatmap(jobId);
      setHeatmapInfo(res.data);

      // Fetch heatmap image with auth headers and create a blob URL for display
      if (res.data?.image_url) {
        try {
          const imgUrl = `${api.defaults.baseURL}${res.data.image_url}`;
          const token = localStorage.getItem("access_token");
          const imgRes = await fetch(imgUrl, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (imgRes.ok) {
            const blob = await imgRes.blob();
            setHeatmapBlobUrl((prev) => {
              if (prev) URL.revokeObjectURL(prev);
              return URL.createObjectURL(blob);
            });
          }
        } catch {
          // Image fetch failed; heatmapBlobUrl stays null
        }
      }
    } catch {
      setHeatmapInfo(null);
      setHeatmapBlobUrl(null);
    } finally {
      setHeatmapLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  useEffect(() => {
    if (activeSubTab === "events") {
      fetchEvents();
    } else if (activeSubTab === "report") {
      fetchReport();
    } else if (activeSubTab === "heatmap") {
      fetchHeatmap();
    }
  }, [activeSubTab, fetchEvents, fetchReport, fetchHeatmap]);

  const handleRerun = async () => {
    setRefreshing(true);
    try {
      const res = await runModule4Job(jobId);
      setData(res.data);
      if (activeSubTab === "events") fetchEvents();
      if (activeSubTab === "report") fetchReport();
      if (activeSubTab === "heatmap") fetchHeatmap();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to refresh analysis.");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center">
        <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading Module 4 Attention Engine results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-red-500/5 border border-red-500/20 rounded-2xl">
        <p className="text-sm font-medium text-red-400 mb-2">Attention Analysis Unavailable</p>
        <p className="text-xs text-gray-500 max-w-md mx-auto mb-4">{error}</p>
        <button
          onClick={handleRerun}
          disabled={refreshing}
          className="px-4 py-2 rounded-xl text-xs font-medium text-white bg-violet-600 hover:bg-violet-500 transition-all shadow-lg"
        >
          {refreshing ? "Computing..." : "Re-evaluate"}
        </button>
      </div>
    );
  }

  const summary = data?.summary || {};
  const shelves = data?.shelves || [];
  const products = data?.products || [];
  const quality = data?.quality_metrics || {};

  // Filtered events
  const filteredEvents = events.filter((ev) => {
    if (eventFilter.direction && ev.attention_direction !== eventFilter.direction) {
      return false;
    }
    if (eventFilter.search) {
      const q = eventFilter.search.toLowerCase();
      const matchTarget = ev.target_name?.toLowerCase().includes(q);
      const matchTrack = String(ev.track_id).includes(q);
      if (!matchTarget && !matchTrack) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* ── Scientific Disclaimer Banner ───────────────────────── */}
      <div className="p-3.5 px-4 rounded-xl bg-violet-950/30 border border-violet-800/30 flex items-start gap-3">
        <div className="w-5 h-5 rounded-lg bg-violet-500/20 text-violet-300 flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-xs font-semibold text-violet-200">
            Head-Pose-Based Attention Estimation Active
          </p>
          <p className="text-[11px] text-violet-300/70 mt-0.5 leading-relaxed">
            All attention metrics are estimated from 3D head pose and orientation (yaw/pitch/roll)
            intersecting configured regions. Physical zone dwell time and active shelf attention
            durations are strictly segregated.
          </p>
        </div>
        <button
          onClick={handleRerun}
          disabled={refreshing}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-600/30 hover:bg-violet-600/50 text-violet-200 border border-violet-500/30 transition-all flex items-center gap-1.5 flex-shrink-0"
        >
          {refreshing ? (
            <div className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          Re-evaluate
        </button>
      </div>

      {/* ── Sub-navigation ────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 border-b border-gray-800 pb-3">
        {[
          { id: "overview", label: "Overview & Shelf Engagement", icon: "📊" },
          { id: "products", label: "Product Focus", icon: "🛍️" },
          { id: "events", label: `Attention Events (${summary.total_attention_events || 0})`, icon: "🎯" },
          { id: "heatmap", label: "Attention Heatmap", icon: "🔥" },
          { id: "report", label: "Full Report & Details", icon: "📄" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveSubTab(tab.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 ${activeSubTab === tab.id
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/20"
                : "bg-gray-800/40 text-gray-400 hover:text-gray-200 hover:bg-gray-800/70"
              }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB 1: Overview & Shelf Engagement ────────────────── */}
      {activeSubTab === "overview" && (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3.5">
            <MetricCard
              label="Total Attention Events"
              value={summary.total_attention_events}
              gradient="from-violet-500 to-indigo-600"
              subtitle="Grouped sustained events"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              }
            />
            <MetricCard
              label="Shelf Attention Time"
              value={`${summary.total_shelf_attention_time_sec ?? 0}s`}
              gradient="from-emerald-500 to-teal-600"
              subtitle="Active shelf viewing"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Avg Event Duration"
              value={`${summary.average_attention_duration_sec ?? 0}s`}
              gradient="from-cyan-500 to-blue-600"
              subtitle="Mean sustained focus"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              }
            />
            <MetricCard
              label="Repeated Visits"
              value={summary.total_repeated_attention_events}
              gradient="from-pink-500 to-rose-600"
              subtitle="Re-engagement events"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              }
            />
            <MetricCard
              label="Unique Viewers"
              value={summary.total_unique_viewers}
              gradient="from-amber-500 to-orange-600"
              subtitle="Shoppers with active gaze"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Face Detection Rate"
              value={quality?.face_detection_rate ? `${(quality.face_detection_rate * 100).toFixed(1)}%` : "—"}
              gradient="from-purple-500 to-fuchsia-600"
              subtitle="Landmark quality score"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
          </div>

          {/* Shelf Engagement Table */}
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white">Shelf Engagement Breakdown</h4>
                <p className="text-xs text-gray-500">
                  Dwell time vs. actual shelf attention duration & analytical engagement score
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800/50 bg-gray-950/40">
                    <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-500 uppercase">Shelf</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Visitors</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Viewers</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Dwell Time</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Shelf Attention</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Avg Attention</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Repeated</th>
                    <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-500 uppercase">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/40 text-sm">
                  {shelves.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-6 text-center text-xs text-gray-500">
                        No shelf regions configured for this camera.
                      </td>
                    </tr>
                  ) : (
                    shelves.map((s) => (
                      <tr key={s.shelf_id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-3">
                          <p className="font-medium text-white">{s.shelf_name}</p>
                          <p className="text-[11px] text-gray-500 font-mono">{s.shelf_id}</p>
                        </td>
                        <td className="px-4 py-3 text-center text-gray-300">{s.visitors}</td>
                        <td className="px-4 py-3 text-center text-emerald-400 font-medium">{s.viewers}</td>
                        <td className="px-4 py-3 text-center text-gray-400">{s.dwell_time_sec.toFixed(1)}s</td>
                        <td className="px-4 py-3 text-center font-semibold text-white">
                          {s.shelf_attention_time_sec.toFixed(1)}s
                        </td>
                        <td className="px-4 py-3 text-center text-gray-400">
                          {s.average_shelf_attention_sec.toFixed(2)}s
                        </td>
                        <td className="px-4 py-3 text-center text-rose-400 font-medium">
                          {s.repeated_attention_events}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <ScoreBadge score={s.score} />
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

      {/* ── TAB 2: Product Focus ──────────────────────────────── */}
      {activeSubTab === "products" && (
        <div className="space-y-4">
          {!summary.product_mapping_configured && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs leading-relaxed">
              <p className="font-semibold mb-1">ℹ️ Product Spatial Mapping Not Configured</p>
              Individual product bounding polygons on the shelves have not been calibrated for this
              camera. Shelf-level attention is active and reliable. Product focus duration will be
              populated when product polygons are configured.
            </div>
          )}

          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-800">
              <h4 className="text-sm font-semibold text-white">Product Attention Metrics</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800/50 bg-gray-950/40">
                    <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-500 uppercase">Product</th>
                    <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-500 uppercase">SKU</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Viewers</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Focus Duration</th>
                    <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-500 uppercase">Repeated</th>
                    <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/40 text-sm">
                  {products.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-xs text-gray-500">
                        No product records available.
                      </td>
                    </tr>
                  ) : (
                    products.map((p) => (
                      <tr key={p.product_id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-3 font-medium text-white">{p.product_name}</td>
                        <td className="px-4 py-3 text-xs text-gray-400 font-mono">{p.sku || "—"}</td>
                        <td className="px-4 py-3 text-center text-gray-300">
                          {p.is_configured ? p.viewers : "—"}
                        </td>
                        <td className="px-4 py-3 text-center text-gray-300">
                          {p.is_configured ? `${p.total_focus_duration_sec.toFixed(1)}s` : "—"}
                        </td>
                        <td className="px-4 py-3 text-center text-gray-300">
                          {p.is_configured ? p.repeated_attention_events : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded text-[10px] font-medium border ${p.is_configured
                                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                                : "bg-gray-800 text-gray-400 border-gray-700"
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

      {/* ── TAB 3: Attention Events ───────────────────────────── */}
      {activeSubTab === "events" && (
        <div className="space-y-4">
          {/* Event Filters */}
          <div className="flex flex-wrap items-center gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800">
            <input
              type="text"
              placeholder="Search target or Track ID..."
              value={eventFilter.search}
              onChange={(e) => setEventFilter((prev) => ({ ...prev, search: e.target.value }))}
              className="px-3 py-1.5 bg-gray-800/70 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50"
            />
            <select
              value={eventFilter.direction}
              onChange={(e) => setEventFilter((prev) => ({ ...prev, direction: e.target.value }))}
              className="px-3 py-1.5 bg-gray-800/70 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-violet-500/50"
            >
              <option value="">All Directions</option>
              <option value="LEFT">LEFT</option>
              <option value="RIGHT">RIGHT</option>
              <option value="CENTER">CENTER</option>
              <option value="UP">UP</option>
              <option value="DOWN">DOWN</option>
            </select>
          </div>

          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden">
            {eventsLoading ? (
              <div className="p-8 text-center">
                <div className="w-6 h-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-gray-500">Loading events...</p>
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">No matching attention events found.</div>
            ) : (
              <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
                <table className="w-full">
                  <thead className="sticky top-0 bg-gray-950/90 backdrop-blur border-b border-gray-800">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-500 uppercase">Track ID</th>
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-500 uppercase">Target</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Direction</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Start / End</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Duration</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Visit #</th>
                      <th className="px-4 py-2.5 text-right text-[11px] font-medium text-gray-500 uppercase">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/30 text-xs">
                    {filteredEvents.map((ev) => (
                      <tr key={ev.event_id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-mono font-medium text-violet-300">
                          Shopper #{ev.track_id}
                        </td>
                        <td className="px-4 py-2.5 text-white font-medium">
                          {ev.target_name}
                          <span className="text-[10px] text-gray-500 ml-1.5 font-mono uppercase">
                            ({ev.target_type})
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <DirectionBadge direction={ev.attention_direction} />
                        </td>
                        <td className="px-4 py-2.5 text-center text-gray-400 font-mono">
                          {ev.start_time.toFixed(2)}s → {ev.end_time ? `${ev.end_time.toFixed(2)}s` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-center font-semibold text-emerald-400">
                          {ev.duration_seconds ? `${ev.duration_seconds.toFixed(2)}s` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-center text-gray-300">
                          {ev.visit_number > 1 ? (
                            <span className="text-rose-400 font-semibold">Visit #{ev.visit_number}</span>
                          ) : (
                            <span>1st Visit</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-right text-gray-400 font-mono">
                          {(ev.confidence * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 4: Attention Heatmap ──────────────────────────── */}
      {activeSubTab === "heatmap" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-sm font-semibold text-white">Camera Space Attention Density</h4>
                <p className="text-xs text-gray-500">
                  2D spatial density of estimated gaze projections across the camera view
                </p>
              </div>
              {heatmapInfo?.total_points != null && (
                <span className="text-xs text-gray-400 font-mono bg-gray-800 px-2.5 py-1 rounded-lg">
                  {heatmapInfo.total_points} gaze points
                </span>
              )}
            </div>

            {heatmapLoading ? (
              <div className="py-12 text-center">
                <div className="w-6 h-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-gray-500">Loading spatial attention heatmap...</p>
              </div>
            ) : heatmapBlobUrl ? (
              <div className="relative aspect-video max-w-2xl mx-auto bg-gray-950 rounded-xl overflow-hidden border border-gray-800">
                <img
                  src={heatmapBlobUrl}
                  alt="Attention Density Heatmap"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = "none";
                  }}
                />
              </div>
            ) : heatmapInfo?.total_points === 0 ? (
              <div className="py-12 text-center text-xs text-gray-500">
                No attention gaze points were detected for heatmap rendering.
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-gray-500">
                Heatmap rendering is generated after pipeline completion.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 5: Report & Details ───────────────────────────── */}
      {activeSubTab === "report" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            {/* Header controls */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-gray-800">
              <div>
                <h4 className="text-sm font-semibold text-white">Module 4 Attention Analysis Report</h4>
                <p className="text-xs text-gray-500">
                  Detailed 3D head pose and shelf engagement analytics exportable in Markdown and JSON
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* View Mode Toggle */}
                <div className="flex bg-gray-800 p-1 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setReportViewMode("markdown")}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                      reportViewMode === "markdown"
                        ? "bg-violet-600 text-white"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    Markdown Report
                  </button>
                  <button
                    type="button"
                    onClick={() => setReportViewMode("json")}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                      reportViewMode === "json"
                        ? "bg-violet-600 text-white"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    Raw JSON
                  </button>
                </div>

                {/* Copy Button */}
                <button
                  type="button"
                  onClick={() => {
                    const content =
                      reportViewMode === "markdown"
                        ? markdownReport || generateModule4FallbackMarkdown(summary, shelves, products, quality)
                        : JSON.stringify(jsonReport || data, null, 2);
                    if (!content) return;
                    navigator.clipboard.writeText(content);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium border border-gray-700 flex items-center gap-1.5 transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  {copied ? "Copied!" : "Copy"}
                </button>

                {/* Download Markdown */}
                <button
                  type="button"
                  onClick={() => {
                    const content = markdownReport || generateModule4FallbackMarkdown(summary, shelves, products, quality);
                    const blob = new Blob([content], { type: "text/markdown" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `module4_attention_report_${jobId}.md`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-violet-600/30 hover:bg-violet-600/50 text-violet-200 text-xs font-medium border border-violet-500/30 flex items-center gap-1.5 transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download .md
                </button>

                {/* Download JSON */}
                <button
                  type="button"
                  onClick={() => {
                    const content = JSON.stringify(jsonReport || data, null, 2);
                    const blob = new Blob([content], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `module4_attention_report_${jobId}.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 flex items-center gap-1.5 transition-all"
                >
                  Download .json
                </button>
              </div>
            </div>

            {/* Content view */}
            {reportLoading ? (
              <div className="p-12 text-center text-xs text-gray-500">Loading formatted report...</div>
            ) : reportViewMode === "markdown" ? (
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap max-h-[500px] overflow-y-auto leading-relaxed bg-gray-950/70 p-4 rounded-xl border border-gray-800">
                {markdownReport || generateModule4FallbackMarkdown(summary, shelves, products, quality)}
              </pre>
            ) : (
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap max-h-[500px] overflow-y-auto leading-relaxed bg-gray-950/70 p-4 rounded-xl border border-gray-800">
                {JSON.stringify(jsonReport || data, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function generateModule4FallbackMarkdown(summary, shelves, products, quality) {
  const lines = [
    "# Module 4 — Consumer Attention Analysis Report",
    "",
    "> **Estimated Attention Analysis**: All metrics derived from 3D head orientation and proxy intersections.",
    "",
    "## 1. Executive Summary",
    "",
    "| Metric | Value |",
    "| :--- | :--- |",
    `| **Total Attention Events** | ${summary.total_attention_events ?? 0} |`,
    `| **Total Attention Duration** | ${(summary.total_attention_duration_sec ?? 0).toFixed(2)}s |`,
    `| **Average Event Duration** | ${(summary.average_attention_duration_sec ?? 0).toFixed(2)}s |`,
    `| **Total Dwell Time** | ${(summary.total_dwell_time_sec ?? 0).toFixed(2)}s |`,
    `| **Total Shelf Attention Time** | ${(summary.total_shelf_attention_time_sec ?? 0).toFixed(2)}s |`,
    `| **Repeated Attention Events** | ${summary.total_repeated_attention_events ?? 0} |`,
    `| **Unique Viewers** | ${summary.total_unique_viewers ?? 0} |`,
    `| **Average Shelf Engagement Score** | ${(summary.shelf_engagement_score_avg ?? 0).toFixed(1)} / 100 |`,
    "",
    "## 2. Shelf Engagement Analysis",
    "",
    "| Shelf Name | Visitors | Viewers | Dwell Time | Attention Time | Avg Attention | Score |",
    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ];

  if (shelves && shelves.length > 0) {
    shelves.forEach((s) => {
      lines.push(
        `| **${s.shelf_name || "—"}** | ${s.visitors ?? 0} | ${s.viewers ?? 0} | ${(s.dwell_time_sec ?? 0).toFixed(1)}s | ${(s.shelf_attention_time_sec ?? 0).toFixed(1)}s | ${(s.average_shelf_attention_sec ?? 0).toFixed(2)}s | **${(s.score ?? 0).toFixed(1)}** |`
      );
    });
  } else {
    lines.push("| *No shelf regions configured* | — | — | — | — | — | — |");
  }

  lines.push("", "## 3. Product Attention Analysis", "");
  if (products && products.length > 0) {
    lines.push(
      "| Product Name | SKU | Viewers | Attention Events | Focus Duration | Avg Focus |",
      "| :--- | :--- | :--- | :--- | :--- | :--- |"
    );
    products.forEach((p) => {
      lines.push(
        `| **${p.product_name || "—"}** | ${p.sku || "—"} | ${p.viewers ?? 0} | ${p.attention_events ?? 0} | ${(p.total_focus_duration_sec ?? 0).toFixed(1)}s | ${(p.average_focus_duration_sec ?? 0).toFixed(2)}s |`
      );
    });
  } else {
    lines.push(
      "> [!WARNING]",
      "> **Product Spatial Mapping Not Configured**: Pixel coordinates for individual products are not mapped."
    );
  }

  if (quality) {
    lines.push(
      "",
      "## 4. Detection Quality & Pose Confidence",
      "",
      "| Quality Metric | Value |",
      "| :--- | :--- |",
      `| **Total Frames Analyzed** | ${quality.total_frames_analyzed ?? 0} |`,
      `| **Valid Face Detections** | ${quality.valid_face_detections ?? 0} |`,
      `| **Face Detection Rate** | ${((quality.face_detection_rate ?? 0) * 100).toFixed(1)}% |`,
      `| **Average Pose Confidence** | ${(quality.average_pose_confidence ?? 0).toFixed(2)} |`
    );
  }

  return lines.join("\n");
}

