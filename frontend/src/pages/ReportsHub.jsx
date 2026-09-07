/**
 * Retail Intelligence Reports & Export Hub (Module 12)
 * =====================================================
 * Centralized reporting studio for generating, previewing, and downloading
 * executive dossiers (PDF) and structured workbooks (Excel, CSV, JSON)
 * across 5 retail intelligence domains:
 * 1. Consumer Attention & Gaze Dossier
 * 2. Product Interaction & Engagement Ledger
 * 3. Shelf Performance & Planogram Audit
 * 4. Conversion Analysis & Attractiveness Scoring
 * 5. Marketing & Promotional Display Effectiveness
 */

import { useState, useEffect, useCallback } from "react";
import PageHeader from "../components/ui/PageHeader";
import { getStores } from "../services/storeService";
import { reportService } from "../services/reportService";
import { useToast } from "../context/ToastContext";

const DOMAIN_ICONS = {
  consumer_attention: "👁️",
  product_engagement: "🛍️",
  shelf_performance: "🏬",
  conversion_analysis: "🎯",
  marketing_effectiveness: "🏆",
};

export default function ReportsHub() {
  const { addToast } = useToast();

  // Stores & Filters
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [datePreset, setDatePreset] = useState("last_7d");

  // Templates & Active Preview
  const [templates, setTemplates] = useState([]);
  const [activeType, setActiveType] = useState("consumer_attention");
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Generation & Ledger
  const [generatingFormat, setGeneratingFormat] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [tableSearch, setTableSearch] = useState("");

  // 1. Initial Load: Stores & Templates
  useEffect(() => {
    async function init() {
      try {
        const [storesRes, templatesRes] = await Promise.all([
          getStores().catch(() => ({ data: [] })),
          reportService.getTemplates().catch(() => []),
        ]);
        const storeList = storesRes.data || [];
        setStores(storeList);
        if (storeList.length > 0) {
          setSelectedStore(storeList[0].id);
        }
        setTemplates(templatesRes);
      } catch (err) {
        console.error("Initialization error in Reports Hub:", err);
      }
    }
    init();
  }, []);

  // 2. Fetch Live Preview when Store or Active Report Type Changes
  const fetchPreview = useCallback(async () => {
    if (!activeType) return;
    setPreviewLoading(true);
    try {
      const res = await reportService.previewReport({
        report_type: activeType,
        store_id: selectedStore || null,
      });
      setPreviewData(res);
    } catch (err) {
      console.error("Failed to load report preview:", err);
      addToast({
        type: "error",
        title: "Preview Unavailable",
        message: err.response?.data?.detail || "Could not generate report preview.",
      });
    } finally {
      setPreviewLoading(false);
    }
  }, [activeType, selectedStore, addToast]);

  useEffect(() => {
    fetchPreview();
  }, [fetchPreview]);

  // 3. Fetch Ledger History
  const fetchLedger = useCallback(async () => {
    setLedgerLoading(true);
    try {
      const res = await reportService.getLedger({
        store_id: selectedStore || undefined,
        limit: 15,
      });
      setLedger(res.reports || []);
    } catch (err) {
      console.error("Failed to load report ledger:", err);
    } finally {
      setLedgerLoading(false);
    }
  }, [selectedStore]);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  // 4. Handle Server-Side Report Generation & Download
  const handleGenerateAndDownload = async (reportType, format) => {
    setGeneratingFormat(format);
    addToast({
      type: "info",
      title: "Compiling Report",
      message: `Generating official ${format.toUpperCase()} dossier...`,
    });

    try {
      const record = await reportService.generateReport({
        report_type: reportType,
        format: format,
        store_id: selectedStore || null,
      });

      addToast({
        type: "success",
        title: "Report Compiled",
        message: `Downloading ${record.title} (${record.file_size_formatted})`,
      });

      // Trigger automatic browser download
      await reportService.downloadReport(record.id, `${record.report_type}.${format === "excel" ? "xlsx" : format}`);
      // Refresh ledger
      fetchLedger();
    } catch (err) {
      console.error("Report generation failed:", err);
      addToast({
        type: "error",
        title: "Generation Failed",
        message: err.response?.data?.detail || "Could not compile report artifact.",
      });
    } finally {
      setGeneratingFormat(null);
    }
  };

  // 5. Client-Side Instant Table CSV Export
  const handleExportClientCSV = () => {
    if (!previewData || !previewData.table_rows?.length) return;
    const headers = previewData.table_headers.map((h) => h.label);
    const keys = previewData.table_headers.map((h) => h.key);
    const csvRows = [headers.join(",")];

    for (const row of previewData.table_rows) {
      const values = keys.map((k) => `"${(row[k] ?? "").toString().replace(/"/g, '""')}"`);
      csvRows.push(values.join(","));
    }

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${activeType}_table_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    addToast({
      type: "success",
      title: "Table Exported",
      message: "Instant CSV downloaded directly from active preview.",
    });
  };

  // Filtered Table Rows
  const filteredRows = (previewData?.table_rows || []).filter((r) => {
    if (!tableSearch.trim()) return true;
    return Object.values(r).some((v) =>
      String(v).toLowerCase().includes(tableSearch.toLowerCase())
    );
  });

  return (
    <div className="space-y-8 pb-12">
      {/* ── Header ─────────────────────────────────────────────── */}
      <PageHeader
        title="Retail Intelligence & Reporting Hub"
        description="Generate, preview, and export executive dossiers and structured operational ledgers across 5 retail intelligence domains."
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        }
      />

      {/* ── Global Filter Bar ──────────────────────────────────── */}
      <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-4 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-[11px] font-semibold tracking-wider uppercase text-gray-400 mb-1">
              Store Scope
            </label>
            <select
              value={selectedStore}
              onChange={(e) => setSelectedStore(e.target.value)}
              className="bg-gray-950/80 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 min-w-[200px]"
            >
              <option value="">🏢 All Stores Fleetwide</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  🏬 {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold tracking-wider uppercase text-gray-400 mb-1">
              Analysis Window
            </label>
            <select
              value={datePreset}
              onChange={(e) => setDatePreset(e.target.value)}
              className="bg-gray-950/80 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 min-w-[160px]"
            >
              <option value="today">Today</option>
              <option value="yesterday">Yesterday</option>
              <option value="last_7d">Last 7 Days (Consolidated)</option>
              <option value="last_30d">Last 30 Days (Monthly)</option>
              <option value="quarter">Current Quarter (Q3)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchPreview}
            disabled={previewLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800/80 hover:bg-gray-700/80 border border-gray-700/60 rounded-xl text-xs font-semibold text-gray-200 transition-all"
          >
            <svg className={`w-3.5 h-3.5 ${previewLoading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Preview
          </button>
        </div>
      </div>

      {/* ── Report Catalog: 5 Domain Cards ─────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold tracking-wide uppercase text-gray-400 flex items-center gap-2">
            <span>📋</span> Report Catalog (5 Mandated Dossiers)
          </h2>
          <span className="text-xs text-gray-400">Select a template to inspect live data</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {templates.map((tpl) => {
            const isSelected = activeType === tpl.report_type;
            const icon = DOMAIN_ICONS[tpl.report_type] || "📄";

            return (
              <div
                key={tpl.report_type}
                onClick={() => setActiveType(tpl.report_type)}
                className={`relative group rounded-2xl p-4 cursor-pointer transition-all duration-300 border flex flex-col justify-between ${
                  isSelected
                    ? "bg-gradient-to-b from-cyan-950/40 to-gray-900/90 border-cyan-500/80 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/40"
                    : "bg-gray-900/50 hover:bg-gray-900/80 border-gray-800/80 hover:border-gray-700"
                }`}
              >
                <div>
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-2xl p-2 rounded-xl bg-gray-950/60 border border-gray-800">
                      {icon}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">
                      {tpl.category}
                    </span>
                  </div>

                  <h3 className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors line-clamp-1">
                    {tpl.title}
                  </h3>
                  <p className="text-[11px] text-gray-400 mt-1 line-clamp-2 leading-relaxed">
                    {tpl.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between">
                  <span className="text-[10px] text-cyan-400/90 font-medium">
                    {tpl.recommended_role}
                  </span>
                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      title="Quick Export PDF"
                      onClick={() => handleGenerateAndDownload(tpl.report_type, "pdf")}
                      className="px-2 py-1 bg-red-950/40 hover:bg-red-900/60 border border-red-800/50 rounded-lg text-[10px] font-bold text-red-300 transition-all"
                    >
                      PDF
                    </button>
                    <button
                      title="Quick Export Excel"
                      onClick={() => handleGenerateAndDownload(tpl.report_type, "excel")}
                      className="px-2 py-1 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-800/50 rounded-lg text-[10px] font-bold text-emerald-300 transition-all"
                    >
                      XLS
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Interactive Live Preview Studio ────────────────────── */}
      <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl shadow-2xl overflow-hidden">
        {/* Studio Header */}
        <div className="p-5 border-b border-gray-800/80 flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-gray-900/90 via-gray-900/60 to-gray-950/90">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">{DOMAIN_ICONS[activeType] || "📊"}</span>
              <h3 className="text-base font-bold text-white">
                {previewData?.title || "Retail Intelligence Preview"}
              </h3>
              <span className="px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/50 text-[10px] font-semibold text-cyan-300">
                Live Preview
              </span>
            </div>
            <p className="text-xs text-gray-400">
              Scope: <span className="text-gray-200 font-medium">{previewData?.store_name}</span> | Period:{" "}
              <span className="text-gray-200 font-medium">{previewData?.date_range_label}</span>
            </p>
          </div>

          {/* Export CTAs */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleExportClientCSV}
              className="px-3.5 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-xs font-semibold text-gray-200 rounded-xl transition-all flex items-center gap-1.5"
            >
              <span>📄</span> Export CSV
            </button>
            <button
              disabled={generatingFormat !== null}
              onClick={() => handleGenerateAndDownload(activeType, "excel")}
              className="px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-xs font-semibold text-white rounded-xl shadow-lg shadow-emerald-900/30 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <span>📊</span> Download Excel
            </button>
            <button
              disabled={generatingFormat !== null}
              onClick={() => handleGenerateAndDownload(activeType, "pdf")}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-xs font-semibold text-white rounded-xl shadow-lg shadow-cyan-900/30 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <span>📥</span> Generate Official PDF
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Executive KPI Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(previewData?.summary_kpis || {}).map(([key, kpi]) => (
              <div
                key={key}
                className="bg-gray-950/60 border border-gray-800/80 rounded-xl p-4 flex flex-col justify-between hover:border-gray-700 transition-colors"
              >
                <span className="text-xs text-gray-400 font-medium">{kpi.label}</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-xl font-bold text-white tracking-tight">{kpi.value}</span>
                  <span className="text-[11px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded-full">
                    {kpi.change}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Strategic Takeaways Box */}
          {previewData?.insights?.length > 0 && (
            <div className="bg-gradient-to-br from-blue-950/20 via-gray-950/60 to-gray-900/40 border border-blue-800/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2 text-blue-400 font-bold text-xs">
                <span>💡</span> STRATEGIC TAKEAWAYS & PRESCRIPTIVE INSIGHTS
              </div>
              <ul className="space-y-1.5 text-xs text-gray-300">
                {previewData.insights.map((ins, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-cyan-400">•</span>
                    <span>{ins}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tabular Breakdown Preview */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                Detailed Analytical Breakdown ({filteredRows.length} Records)
              </h4>
              <input
                type="text"
                placeholder="Search records..."
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                className="bg-gray-950/80 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 w-48"
              />
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-800/80">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-gray-950/90 text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-800 font-semibold">
                  <tr>
                    {(previewData?.table_headers || []).map((h) => (
                      <th
                        key={h.key}
                        className={`px-4 py-3 ${
                          h.align === "right" ? "text-right" : h.align === "center" ? "text-center" : "text-left"
                        }`}
                      >
                        {h.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {filteredRows.length === 0 ? (
                    <tr>
                      <td colSpan={previewData?.table_headers?.length || 4} className="px-4 py-8 text-center text-gray-400">
                        No records matching filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                        {(previewData?.table_headers || []).map((h) => {
                          const val = row[h.key];
                          const isGrade = h.key.includes("grade") || h.key.includes("rating");
                          const isDead = val === "Dead Zone";

                          return (
                            <td
                              key={h.key}
                              className={`px-4 py-3 ${
                                h.align === "right" ? "text-right" : h.align === "center" ? "text-center" : "text-left"
                              }`}
                            >
                              {isGrade ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800/50">
                                  {val}
                                </span>
                              ) : isDead ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-950/80 text-red-300 border border-red-800/50">
                                  {val}
                                </span>
                              ) : (
                                <span className={h.key === "product_name" || h.key === "shelf_name" ? "font-semibold text-white" : ""}>
                                  {val ?? "—"}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* ── Historical Report Ledger & Audit Trail ─────────────── */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>📜</span> Generated Dossiers & Audit Ledger
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Historical archive of compiled PDF, Excel, and CSV files ready for download.
            </p>
          </div>
          <button
            onClick={fetchLedger}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
          >
            Refresh Ledger
          </button>
        </div>

        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-gray-950 text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-800">
              <tr>
                <th className="px-4 py-3">Report Title</th>
                <th className="px-4 py-3">Domain Type</th>
                <th className="px-4 py-3 text-center">Format</th>
                <th className="px-4 py-3">Store Location</th>
                <th className="px-4 py-3 text-right">File Size</th>
                <th className="px-4 py-3">Generated At</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {ledger.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    No reports generated yet. Click &apos;Generate Official PDF&apos; or &apos;Download Excel&apos; above to compile your first dossier.
                  </td>
                </tr>
              ) : (
                ledger.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-3 font-semibold text-white">
                      {item.title}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {item.report_type.replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        item.format === "pdf"
                          ? "bg-red-950/60 text-red-400 border border-red-800/40"
                          : item.format === "excel" || item.format === "xlsx"
                          ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"
                          : "bg-blue-950/60 text-blue-400 border border-blue-800/40"
                      }`}>
                        {item.format}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {item.store_name}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-400">
                      {item.file_size_formatted}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => reportService.downloadReport(item.id, `${item.report_type}.${item.format === "excel" ? "xlsx" : item.format}`)}
                        className="px-3 py-1 bg-cyan-950/80 hover:bg-cyan-900/80 border border-cyan-700/60 text-cyan-300 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1"
                      >
                        <span>📥</span> Download
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
