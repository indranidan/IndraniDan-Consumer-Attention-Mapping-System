import React, { useEffect } from "react";
import { UnifiedJobProvider, useUnifiedJobContext } from "../../context/UnifiedJobContext";
import SummaryTab from "./tabs/SummaryTab";
import BehaviorTab from "./tabs/BehaviorTab";
import HeatmapsTab from "./tabs/HeatmapsTab";
import ScoringTab from "./tabs/ScoringTab";
import RecommendationsTab from "./tabs/RecommendationsTab";
import MatrixTab from "./tabs/MatrixTab";
import LogsTab from "./tabs/LogsTab";
import ReportsTab from "./tabs/ReportsTab";

function UnifiedAIJobResultsModalContent() {
  const {
    jobId,
    job,
    isOpen,
    onClose,
    activeTab,
    setActiveTab,
    loading,
    error,
    reEvaluating,
    reEvalSuccess,
    handleReEvaluate,
    unifiedData,
  } = useUnifiedJobContext();

  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const m4Analysis = unifiedData?.attention || {};
  const m4Summary = m4Analysis.summary || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 animate-fade-in overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      {/* Expanded Full-Width Modal Window */}
      <div className="relative w-full max-w-7xl max-h-[92vh] flex flex-col bg-gray-950/95 backdrop-blur-2xl border border-gray-800/80 rounded-3xl shadow-2xl shadow-black/80 z-10 overflow-hidden">
        {/* ── Sticky Top Header ────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-4 border-b border-gray-800/80 bg-gray-900/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-600 via-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-violet-600/30">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  AI Consumer Attention & Interaction Intelligence
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {job?.status || "COMPLETED"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                <span>📷 {job?.camera_name || "Camera"}</span>
                <span>•</span>
                <span>🏬 {job?.store_name || "Store"}</span>
                {m4Summary.analyzed_at && (
                  <>
                    <span>•</span>
                    <span className="text-[11px] text-gray-400 font-mono">
                      Cached: {new Date(m4Summary.analyzed_at).toLocaleTimeString()}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Single-Click Re-Evaluate Both Engines */}
            <button
              onClick={handleReEvaluate}
              disabled={reEvaluating || loading}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-lg ${
                reEvaluating
                  ? "bg-violet-600/50 text-violet-200 cursor-not-allowed"
                  : "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white shadow-violet-600/30"
              }`}
              title="Re-run Attention (M4), Interaction (M5), and Behavior (M6) analysis engines"
            >
              <svg
                className={`w-4 h-4 ${reEvaluating ? "animate-spin" : ""}`}
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
              <span>{reEvaluating ? "Re-evaluating Pipeline..." : "Re-evaluate"}</span>
            </button>

            {reEvalSuccess && (
              <span className="text-xs text-emerald-400 font-medium animate-fade-in flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-lg">
                ✓ Updated
              </span>
            )}

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Main Tab Navigation Bar ──────────────────────────────────── */}
        <div className="flex items-center gap-1.5 px-6 py-2.5 border-b border-gray-800/80 bg-gray-950/80 overflow-x-auto shrink-0 scrollbar-none">
          {[
            { id: "summary", label: "Executive Summary & Funnel", icon: "📊" },
            { id: "behavior", label: "Consumer Behavior", icon: "🧠" },
            { id: "heatmaps", label: "Spatial & Heatmaps", icon: "🔥" },
            { id: "scoring", label: "Attractiveness & Scoring", icon: "🎯" },
            { id: "recommendations", label: "Prescriptive Optimization", icon: "💡" },
            { id: "matrix", label: "Shelf & Product Matrix", icon: "📦" },
            { id: "logs", label: "Shopper Journey Logs", icon: "🚶" },
            { id: "reports", label: "Executive Reports", icon: "📝" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-gradient-to-r from-violet-600/90 to-indigo-600/90 text-white shadow-lg shadow-violet-600/20 border border-violet-500/30"
                  : "bg-gray-900/40 text-gray-400 hover:text-white hover:bg-gray-900 border border-transparent"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* ── Modal Body Content ──────────────────────────────────────── */}
        <div className="flex-1 px-6 py-5 overflow-y-auto min-h-0 bg-gray-950">
          {loading ? (
            <div className="py-24 text-center">
              <div className="w-10 h-10 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm font-medium text-gray-300">Loading comprehensive AI job intelligence...</p>
              <p className="text-xs text-gray-500 mt-1">Retrieving tracking, gaze attention, and interaction models</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center bg-red-500/5 border border-red-500/20 rounded-2xl max-w-lg mx-auto my-12">
              <p className="text-sm font-semibold text-red-400 mb-2">Analytics Engine Notice</p>
              <p className="text-xs text-gray-400 mb-4">{error}</p>
              <button
                onClick={handleReEvaluate}
                disabled={reEvaluating}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 transition-all shadow-lg shadow-violet-600/30"
              >
                {reEvaluating ? "Computing..." : "Generate Analysis Now"}
              </button>
            </div>
          ) : (
            <>
              {activeTab === "summary" && <SummaryTab />}
              {activeTab === "behavior" && <BehaviorTab />}
              {activeTab === "heatmaps" && <HeatmapsTab />}
              {activeTab === "scoring" && <ScoringTab />}
              {activeTab === "recommendations" && <RecommendationsTab />}
              {activeTab === "matrix" && <MatrixTab />}
              {activeTab === "logs" && <LogsTab />}
              {activeTab === "reports" && <ReportsTab />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function UnifiedAIJobResultsModal(props) {
  return (
    <UnifiedJobProvider {...props}>
      <UnifiedAIJobResultsModalContent />
    </UnifiedJobProvider>
  );
}
