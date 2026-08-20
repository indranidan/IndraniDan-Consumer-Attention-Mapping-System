/**
 * Module 3 — Tracking & Movement Analytics UI Component
 * =======================================================
 * Displays comprehensive Module 3 analytics:
 * - Executive Overview & High-level Metrics
 * - Multi-Person Tracking & Session Intelligence (ByteTrack)
 * - Spatial Zone Dwell Time & Movement Analytics
 * - Estimated Attention Targets & Head Orientation Metrics
 * - Full Phase 6 Markdown & JSON Report Viewer with Download & Copy
 * - Output Artifacts Browser & Video Player
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getAIJobResults,
  getAIJobReport,
  getAIFileUrl,
} from "../../services/storeService";

function MetricCard({ label, value, icon, gradient, subtitle }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-gray-700/50 transition-all">
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

function StatusBadge({ status }) {
  const isCompleted = status === "completed";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-mono font-medium border ${
        isCompleted
          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isCompleted ? "bg-emerald-400" : "bg-amber-400"
        }`}
      />
      {status}
    </span>
  );
}

export default function Module3TrackingAnalytics({ jobId, job, resultsData }) {
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "shoppers" | "zones" | "targets" | "report" | "files"
  const [data, setData] = useState(resultsData || null);
  const [loading, setLoading] = useState(!resultsData);
  const [error, setError] = useState(null);

  // Report tab states
  const [reportViewMode, setReportViewMode] = useState("markdown"); // "markdown" | "json"
  const [markdownContent, setMarkdownContent] = useState("");
  const [jsonReport, setJsonReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Filter states
  const [shopperSearch, setShopperSearch] = useState("");
  const [shopperStatusFilter, setShopperStatusFilter] = useState("ALL");

  // Video playback
  const [videoUrl, setVideoUrl] = useState(null);

  const fetchResults = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getAIJobResults(jobId);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load Module 3 results.");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const fetchReport = useCallback(async () => {
    if (!jobId) return;
    setReportLoading(true);
    try {
      const res = await getAIJobReport(jobId);
      setMarkdownContent(res.data?.markdown_report || "");
      setJsonReport(res.data?.json_report || null);
    } catch {
      // If endpoint fails, fallback to using data.reports
      if (data?.reports) {
        setJsonReport(data.reports);
      }
      if (data?.markdown_report) {
        setMarkdownContent(data.markdown_report);
      }
    } finally {
      setReportLoading(false);
    }
  }, [jobId, data]);

  useEffect(() => {
    if (!resultsData) {
      fetchResults();
    } else {
      setData(resultsData);
      setLoading(false);
      setError(null);
    }
  }, [resultsData, fetchResults]);

  useEffect(() => {
    if (activeTab === "report") {
      fetchReport();
    }
  }, [activeTab, fetchReport]);

  const summary = data?.summary || data?.reports?.summary || {};
  const shoppers = data?.reports?.shoppers || [];
  const zones = data?.reports?.zones || [];
  const targets = data?.reports?.targets || [];
  const availableFiles = data?.available_files || [];

  // Filtered shoppers list
  const filteredShoppers = useMemo(() => {
    return shoppers.filter((s) => {
      if (shopperStatusFilter !== "ALL" && s.session_status !== shopperStatusFilter) {
        return false;
      }
      if (shopperSearch) {
        const q = shopperSearch.toLowerCase();
        const matchId = String(s.tracking_id).includes(q);
        const matchSession = s.session_id?.toLowerCase().includes(q);
        const matchTarget = s.most_attended_target?.toLowerCase().includes(q);
        if (!matchId && !matchSession && !matchTarget) return false;
      }
      return true;
    });
  }, [shoppers, shopperStatusFilter, shopperSearch]);

  // Group available files by phase
  const groupedFiles = useMemo(() => {
    const groups = {};
    availableFiles.forEach((file) => {
      const parts = file.split(/[\/\\]/);
      const phase = parts[0] || "other";
      if (!groups[phase]) groups[phase] = [];
      groups[phase].push(file);
    });
    return groups;
  }, [availableFiles]);

  const handleCopyReport = () => {
    const content = reportViewMode === "markdown" ? markdownContent : JSON.stringify(jsonReport || data?.reports, null, 2);
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = (format = "md") => {
    let content = "";
    let filename = "";
    let type = "";

    if (format === "md") {
      content = markdownContent || generateFallbackMarkdown(summary, shoppers, zones, targets);
      filename = `module3_tracking_report_${jobId}.md`;
      type = "text/markdown";
    } else {
      content = JSON.stringify(jsonReport || data?.reports || { summary }, null, 2);
      filename = `module3_tracking_report_${jobId}.json`;
      type = "application/json";
    }

    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handlePlayVideo = async (filePath) => {
    try {
      const url = getAIFileUrl(jobId, filePath);
      const token = localStorage.getItem("access_token");
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const blob = await res.blob();
        if (videoUrl) URL.revokeObjectURL(videoUrl);
        setVideoUrl(URL.createObjectURL(blob));
      }
    } catch {
      /* ignore */
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center">
        <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading Module 3 tracking & movement analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-red-500/5 border border-red-500/20 rounded-2xl">
        <p className="text-sm font-medium text-red-400 mb-2">Module 3 Analytics Unavailable</p>
        <p className="text-xs text-gray-500 max-w-md mx-auto mb-4">{error}</p>
        <button
          onClick={fetchResults}
          className="px-4 py-2 rounded-xl text-xs font-medium text-white bg-violet-600 hover:bg-violet-500 transition-all shadow-lg"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Top Pipeline Info Banner ──────────────────────────── */}
      <div className="p-4 rounded-xl bg-violet-950/30 border border-violet-800/30 flex items-start gap-3">
        <div className="w-5 h-5 rounded-lg bg-violet-500/20 text-violet-300 flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-xs font-semibold text-violet-200">
            Module 3 Multi-Phase Tracking & Dwell Intelligence
          </p>
          <p className="text-[11px] text-violet-300/70 mt-0.5 leading-relaxed">
            Covers YOLO Person Detection, ByteTrack Persistent Identification, Trajectory Analysis,
            Zone Dwell Analytics, and Head-Orientation Attention Proxies.
          </p>
        </div>
      </div>

      {/* ── Sub-navigation ────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 border-b border-gray-800 pb-3">
        {[
          { id: "overview", label: "Executive Overview", icon: "📊" },
          { id: "shoppers", label: `Shoppers & Sessions (${shoppers.length || summary.unique_shoppers || 0})`, icon: "👥" },
          { id: "zones", label: `Zone Analytics (${zones.length || 0})`, icon: "📍" },
          { id: "targets", label: `Attention Targets (${targets.length || summary.number_of_attention_targets || 0})`, icon: "🎯" },
          { id: "report", label: "Full Report & Export", icon: "📄" },
          { id: "files", label: `Output Artifacts (${availableFiles.length})`, icon: "📁" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTab === tab.id
                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                : "bg-gray-800/40 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB 1: Executive Overview ─────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Summary Metric Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard
              label="Unique Shoppers"
              value={summary.unique_shoppers ?? shoppers.length ?? 0}
              gradient="from-violet-500 to-indigo-600"
              subtitle="Distinct tracked IDs"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Total Sessions"
              value={summary.total_sessions ?? shoppers.length ?? 0}
              gradient="from-emerald-500 to-teal-600"
              subtitle={`${summary.completed_sessions || 0} completed`}
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              }
            />
            <MetricCard
              label="Zone Visits"
              value={summary.total_zone_visits ?? 0}
              gradient="from-amber-500 to-orange-600"
              subtitle={`Across ${zones.length || 0} zones`}
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Attention Events"
              value={summary.total_attention_events ?? 0}
              gradient="from-pink-500 to-rose-600"
              subtitle="Gaze interactions"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              }
            />
            <MetricCard
              label="Avg Session Duration"
              value={
                summary.average_session_duration_sec != null
                  ? `${summary.average_session_duration_sec.toFixed(2)}s`
                  : "—"
              }
              gradient="from-cyan-500 to-blue-600"
              subtitle="In-camera presence"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Avg Zone Dwell"
              value={
                summary.average_zone_dwell_time_sec != null
                  ? `${summary.average_zone_dwell_time_sec.toFixed(2)}s`
                  : "—"
              }
              gradient="from-purple-500 to-fuchsia-600"
              subtitle="Per zone visit"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <MetricCard
              label="Attention Targets"
              value={summary.number_of_attention_targets ?? targets.length ?? 0}
              gradient="from-lime-500 to-green-600"
              subtitle="Configured shelves/regions"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              }
            />
            <MetricCard
              label="Est. Attention Time"
              value={
                summary.total_estimated_attention_duration_sec != null
                  ? `${summary.total_estimated_attention_duration_sec.toFixed(2)}s`
                  : "—"
              }
              gradient="from-rose-500 to-red-600"
              subtitle="Gaze duration sum"
              icon={
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              }
            />
          </div>

          {/* Highlights & Top Zones */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {summary.most_visited_zone && (
              <div className="bg-gray-900/60 rounded-2xl p-4 border border-gray-800/60">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-violet-400" />
                  <p className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">
                    Most Visited Zone
                  </p>
                </div>
                <p className="text-base font-bold text-white">
                  {summary.most_visited_zone.zone_name || summary.most_visited_zone.zone_id}
                </p>
                <p className="text-xs text-violet-400 mt-1 font-mono font-medium">
                  {summary.most_visited_zone.total_visits} shopper visits
                </p>
              </div>
            )}

            {summary.zone_with_highest_average_dwell && (
              <div className="bg-gray-900/60 rounded-2xl p-4 border border-gray-800/60">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <p className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">
                    Highest Avg Dwell Zone
                  </p>
                </div>
                <p className="text-base font-bold text-white">
                  {summary.zone_with_highest_average_dwell.zone_name || summary.zone_with_highest_average_dwell.zone_id}
                </p>
                <p className="text-xs text-emerald-400 mt-1 font-mono font-medium">
                  {(summary.zone_with_highest_average_dwell.average_dwell_seconds ?? summary.zone_with_highest_average_dwell.average_dwell_time_sec ?? summary.zone_with_highest_average_dwell.average_dwell_sec)?.toFixed(2)}s avg dwell
                </p>
              </div>
            )}

            {summary.most_attended_target && (
              <div className="bg-gray-900/60 rounded-2xl p-4 border border-gray-800/60">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-rose-400" />
                  <p className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">
                    Most Attended Target
                  </p>
                </div>
                <p className="text-base font-bold text-white">
                  {summary.most_attended_target.target_name || summary.most_attended_target.target_id}
                </p>
                <p className="text-xs text-rose-400 mt-1 font-mono font-medium">
                  {(summary.most_attended_target.total_attention_sec ?? summary.most_attended_target.total_estimated_attention_duration_sec)?.toFixed(2)}s total attention
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 2: Shoppers & Sessions ────────────────────────── */}
      {activeTab === "shoppers" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl overflow-hidden p-5">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
              <div>
                <h4 className="text-sm font-semibold text-white">Shopper Sessions & Trajectories</h4>
                <p className="text-xs text-gray-500">
                  ByteTrack Multi-Person Tracking sessions with persistent IDs and dwell statistics
                </p>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <input
                  type="text"
                  placeholder="Search by ID, session, target..."
                  value={shopperSearch}
                  onChange={(e) => setShopperSearch(e.target.value)}
                  className="px-3 py-1.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 w-full sm:w-56"
                />
                <select
                  value={shopperStatusFilter}
                  onChange={(e) => setShopperStatusFilter(e.target.value)}
                  className="px-3 py-1.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-xs text-white focus:outline-none focus:border-violet-500/50"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="completed">Completed</option>
                  <option value="track_lost">Track Lost</option>
                </select>
              </div>
            </div>

            {filteredShoppers.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">
                {shoppers.length === 0 ? "No individual shopper records in report." : "No shoppers matched the filter."}
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[440px] overflow-y-auto">
                <table className="w-full">
                  <thead className="sticky top-0 bg-gray-950/90 backdrop-blur border-b border-gray-800">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-500 uppercase">Shopper ID</th>
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-500 uppercase">Session ID</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Duration</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Zone Visits</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Dwell (s)</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Attn Events</th>
                      <th className="px-4 py-2.5 text-center text-[11px] font-medium text-gray-500 uppercase">Est. Attn (s)</th>
                      <th className="px-4 py-2.5 text-left text-[11px] font-medium text-gray-500 uppercase">Top Target</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/30 text-xs">
                    {filteredShoppers.map((s) => (
                      <tr key={s.tracking_id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-mono font-medium text-violet-300">
                          #{s.tracking_id}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-gray-400 text-[11px]">
                          {s.session_id}
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <StatusBadge status={s.session_status} />
                        </td>
                        <td className="px-4 py-2.5 text-center font-mono text-gray-300">
                          {s.session_duration_sec != null ? `${s.session_duration_sec.toFixed(2)}s` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-center font-mono text-amber-300">
                          {s.number_of_zone_visits ?? s.zones_visited?.length ?? 0}
                        </td>
                        <td className="px-4 py-2.5 text-center font-mono font-semibold text-emerald-400">
                          {s.total_zone_dwell_time_sec != null ? `${s.total_zone_dwell_time_sec.toFixed(2)}s` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-center font-mono text-pink-300">
                          {s.attention_event_count ?? 0}
                        </td>
                        <td className="px-4 py-2.5 text-center font-mono font-semibold text-rose-400">
                          {s.total_estimated_attention_duration_sec != null ? `${s.total_estimated_attention_duration_sec.toFixed(2)}s` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-gray-300 truncate max-w-[140px]">
                          {s.most_attended_target || "—"}
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

      {/* ── TAB 3: Zone Analytics ─────────────────────────────── */}
      {activeTab === "zones" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-white">Spatial Zone Traffic & Dwell Distribution</h4>
              <p className="text-xs text-gray-500">
                Breakdown of visits, unique shoppers, and dwell durations by designated store zone
              </p>
            </div>

            {zones.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">No zone analytics recorded for this run.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {zones.map((z) => (
                  <div
                    key={z.zone_id}
                    className="p-4 rounded-xl bg-gray-950/60 border border-gray-800/80 hover:border-violet-500/30 transition-all space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="text-sm font-semibold text-white">{z.zone_name || z.zone_id}</h5>
                        <p className="text-[10px] text-gray-500 font-mono">ID: {z.zone_id}</p>
                      </div>
                      <span className="px-2.5 py-1 rounded-lg bg-violet-500/10 text-violet-300 border border-violet-500/20 text-xs font-semibold">
                        {z.total_visits || 0} visits
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-gray-800/50">
                      <div className="bg-gray-900/40 p-2 rounded-lg">
                        <p className="text-[10px] text-gray-500 uppercase">Unique Shoppers</p>
                        <p className="text-sm font-bold text-white mt-0.5">{z.unique_shoppers ?? z.unique_visitors ?? "—"}</p>
                      </div>
                      <div className="bg-gray-900/40 p-2 rounded-lg">
                        <p className="text-[10px] text-gray-500 uppercase">Total Dwell</p>
                        <p className="text-sm font-bold text-emerald-400 mt-0.5">
                          {z.total_dwell_time_sec != null ? `${z.total_dwell_time_sec.toFixed(1)}s` : "—"}
                        </p>
                      </div>
                      <div className="bg-gray-900/40 p-2 rounded-lg">
                        <p className="text-[10px] text-gray-500 uppercase">Avg Dwell</p>
                        <p className="text-sm font-bold text-cyan-400 mt-0.5">
                          {z.average_dwell_time_sec != null ? `${z.average_dwell_time_sec.toFixed(2)}s` : "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 4: Attention Targets ──────────────────────────── */}
      {activeTab === "targets" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-white">Estimated Attention Targets</h4>
              <p className="text-xs text-gray-500">
                Attention duration proxy based on head orientation intersecting target regions
              </p>
            </div>

            {targets.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">No attention target records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-950/90 border-b border-gray-800 text-[11px] font-medium text-gray-500 uppercase">
                    <tr>
                      <th className="px-4 py-2.5 text-left">Target Name</th>
                      <th className="px-4 py-2.5 text-center">Total Attention</th>
                      <th className="px-4 py-2.5 text-center">Avg Attention</th>
                      <th className="px-4 py-2.5 text-center">Unique Viewers</th>
                      <th className="px-4 py-2.5 text-center">Attention Events</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/30">
                    {targets.map((t) => {
                      const totalAttn = t.total_estimated_attention_duration_sec ?? t.total_attention_sec;
                      const avgAttn = t.average_attention_duration_sec ?? t.average_attention_sec;
                      const viewers = t.unique_shoppers ?? t.unique_viewers;
                      const events = t.attention_event_count ?? t.total_events;
                      return (
                        <tr key={t.target_id || t.target_name} className="hover:bg-gray-800/30 transition-colors">
                          <td className="px-4 py-3 font-semibold text-white">
                            {t.target_name || t.target_id}
                            {t.target_id && (
                              <span className="text-[10px] text-gray-500 ml-1.5 font-mono">({t.target_id})</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center font-mono font-bold text-rose-400">
                            {totalAttn != null ? `${Number(totalAttn).toFixed(2)}s` : "—"}
                          </td>
                          <td className="px-4 py-3 text-center font-mono text-gray-300">
                            {avgAttn != null ? `${Number(avgAttn).toFixed(2)}s` : "—"}
                          </td>
                          <td className="px-4 py-3 text-center font-mono text-violet-300">
                            {viewers ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-center font-mono text-emerald-400">
                            {events ?? "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 5: Full Report & Details ──────────────────────── */}
      {activeTab === "report" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            {/* Header controls */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-gray-800">
              <div>
                <h4 className="text-sm font-semibold text-white">Module 3 Master Attention & Tracking Report</h4>
                <p className="text-xs text-gray-500">
                  Comprehensive Phase 6 report exportable in Markdown and JSON formats
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Mode Toggle */}
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
                  onClick={handleCopyReport}
                  className="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium border border-gray-700 flex items-center gap-1.5 transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  {copied ? "Copied!" : "Copy"}
                </button>

                {/* Download Buttons */}
                <button
                  type="button"
                  onClick={() => handleDownloadReport("md")}
                  className="px-3 py-1.5 rounded-xl bg-violet-600/30 hover:bg-violet-600/50 text-violet-200 text-xs font-medium border border-violet-500/30 flex items-center gap-1.5 transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download .md
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadReport("json")}
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
                {markdownContent || generateFallbackMarkdown(summary, shoppers, zones, targets)}
              </pre>
            ) : (
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap max-h-[500px] overflow-y-auto leading-relaxed bg-gray-950/70 p-4 rounded-xl border border-gray-800">
                {JSON.stringify(jsonReport || data?.reports || { summary, shoppers, zones, targets }, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 6: Output Artifacts & Media ───────────────────── */}
      {activeTab === "files" && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800/60 rounded-2xl p-5">
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-white">Pipeline Output Artifacts & Media</h4>
              <p className="text-xs text-gray-500">
                Raw output files generated across all 6 phases of the Module 3 pipeline
              </p>
            </div>

            {/* Video preview if available */}
            {videoUrl && (
              <div className="mb-6 p-4 rounded-xl bg-gray-950 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    Annotated Video Preview
                  </span>
                  <button
                    type="button"
                    onClick={() => setVideoUrl(null)}
                    className="text-xs text-gray-400 hover:text-white"
                  >
                    Close Preview
                  </button>
                </div>
                <video src={videoUrl} controls className="w-full max-h-[400px] rounded-lg bg-black" />
              </div>
            )}

            {availableFiles.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500">No output files cataloged for this run.</div>
            ) : (
              <div className="space-y-4">
                {Object.keys(groupedFiles).map((phaseKey) => (
                  <div key={phaseKey} className="bg-gray-950/50 rounded-xl p-4 border border-gray-800/50">
                    <h5 className="text-xs font-bold text-violet-400 uppercase tracking-wider mb-2">
                      {phaseKey.toUpperCase()} Files ({groupedFiles[phaseKey].length})
                    </h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {groupedFiles[phaseKey].map((file) => {
                        const isVideo = file.match(/\.(mp4|avi|mkv)$/i);
                        return (
                          <div
                            key={file}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-gray-900/60 border border-gray-800/50 text-xs font-mono text-gray-300"
                          >
                            <span className="truncate max-w-[240px] text-gray-300" title={file}>
                              {file}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {isVideo && (
                                <button
                                  type="button"
                                  onClick={() => handlePlayVideo(file)}
                                  className="px-2 py-1 rounded bg-violet-600/30 hover:bg-violet-600/50 text-violet-200 text-[10px] font-sans transition-all"
                                >
                                  Play
                                </button>
                              )}
                              <a
                                href={getAIFileUrl(jobId, file)}
                                target="_blank"
                                rel="noreferrer"
                                download
                                className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px] font-sans transition-all"
                              >
                                View / Download
                              </a>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function generateFallbackMarkdown(summary, shoppers, zones, targets) {
  const lines = [
    "# Module 3 — Consumer Tracking & Movement Analytics Report",
    "",
    "> **Phase 6: Executive Attention & Movement Report**",
    "",
    "## 1. Executive Summary",
    "",
    "| Metric | Value |",
    "| :--- | :--- |",
    `| **Total Unique Shoppers** | ${summary.unique_shoppers ?? shoppers.length ?? 0} |`,
    `| **Total Sessions** | ${summary.total_sessions ?? shoppers.length ?? 0} |`,
    `| **Completed Sessions** | ${summary.completed_sessions ?? 0} |`,
    `| **Total Zone Visits** | ${summary.total_zone_visits ?? 0} |`,
    `| **Avg Session Duration** | ${summary.average_session_duration_sec ?? 0}s |`,
    `| **Avg Zone Dwell Time** | ${summary.average_zone_dwell_time_sec ?? 0}s |`,
    `| **Total Attention Events** | ${summary.total_attention_events ?? 0} |`,
    `| **Total Est. Attention Duration** | ${summary.total_estimated_attention_duration_sec ?? 0}s |`,
    "",
    "## 2. Zone Analytics Summary",
    "",
    "| Zone ID | Zone Name | Total Visits | Unique Shoppers | Total Dwell (s) | Avg Dwell (s) |",
    "| :--- | :--- | :--- | :--- | :--- | :--- |",
  ];

  if (zones.length > 0) {
    zones.forEach((z) => {
      lines.push(
        `| ${z.zone_id} | **${z.zone_name || z.zone_id}** | ${z.total_visits || 0} | ${z.unique_shoppers ?? z.unique_visitors ?? 0} | ${(z.total_dwell_time_sec || 0).toFixed(1)}s | ${(z.average_dwell_time_sec || 0).toFixed(2)}s |`
      );
    });
  } else {
    lines.push("| — | *No zone data recorded* | — | — | — | — |");
  }

  lines.push("", "## 3. Attention Targets", "", "| Target | Total Attention (s) | Avg Attention (s) | Unique Viewers |", "| :--- | :--- | :--- | :--- |");
  if (targets.length > 0) {
    targets.forEach((t) => {
      const totalAttn = t.total_estimated_attention_duration_sec ?? t.total_attention_sec ?? 0;
      const avgAttn = t.average_attention_duration_sec ?? t.average_attention_sec ?? 0;
      const viewers = t.unique_shoppers ?? t.unique_viewers ?? 0;
      lines.push(
        `| **${t.target_name || t.target_id}** | ${Number(totalAttn).toFixed(2)}s | ${Number(avgAttn).toFixed(2)}s | ${viewers} |`
      );
    });
  } else {
    lines.push("| — | *No attention targets recorded* | — | — |");
  }

  lines.push(
    "",
    "---",
    "",
    "> *Note: All attention values are estimated based on 3D head orientation and proxy intersections.*"
  );

  return lines.join("\n");
}
