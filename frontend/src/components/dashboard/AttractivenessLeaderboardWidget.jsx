import React, { useState } from "react";

export default function AttractivenessLeaderboardWidget({ leaderboard, loading, onNavigateScoring }) {
  const [tab, setTab] = useState("top"); // "top" or "bottom"

  if (loading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl h-80 animate-pulse flex flex-col justify-between">
        <div className="h-5 w-48 bg-gray-800 rounded" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-9 bg-gray-800/60 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const topPerformers = leaderboard?.top_performers || [];
  const attentionLeaks = leaderboard?.attention_leaks || [];
  const currentList = tab === "top" ? topPerformers : attentionLeaks;

  const getRatingBadge = (rating) => {
    switch (rating) {
      case "A+":
      case "A":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "B":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "C":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    }
  };

  return (
    <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between h-full">
      <div>
        {/* Header & Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🎯</span> Product Attractiveness Leaderboard
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Bayesian 5-Pillar scoring with shelf visibility correction (γ)
            </p>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono">
            Module 8
          </span>
        </div>

        {/* Tab Toggle Buttons */}
        <div className="flex bg-gray-800/60 p-1 rounded-xl border border-gray-700/40 mb-4">
          <button
            onClick={() => setTab("top")}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              tab === "top"
                ? "bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            🌟 Top Performers ({topPerformers.length})
          </button>
          <button
            onClick={() => setTab("bottom")}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              tab === "bottom"
                ? "bg-gradient-to-r from-rose-500 to-amber-600 text-white shadow-md"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            ⚠️ Attention Leaks ({attentionLeaks.length})
          </button>
        </div>

        {/* List of Products */}
        <div className="space-y-2.5">
          {currentList.slice(0, 5).map((p, idx) => {
            const score = p.attractiveness_score ?? 50.0;
            const intrinsic = p.intrinsic_score ?? score;
            const rating = p.rating || (score >= 70 ? "A" : score >= 50 ? "B" : "D");

            return (
              <div
                key={p.product_id || idx}
                className="flex items-center justify-between p-2.5 rounded-xl bg-gray-800/40 hover:bg-gray-800/70 border border-gray-700/30 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono font-bold text-gray-500 w-4">
                    #{idx + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white truncate max-w-[150px] sm:max-w-[200px]">
                      {p.product_name || "Product"}
                    </p>
                    <p className="text-[10px] text-gray-400 truncate">
                      {p.category || "General"} • {p.shelf_name || "Shelf"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* Intrinsic vs Observed Mini Badge */}
                  <div className="text-right hidden sm:block">
                    <span className="text-xs font-bold font-mono text-white">
                      {score.toFixed(1)}
                    </span>
                    <p className="text-[9px] text-gray-500">
                      Intrinsic: {intrinsic.toFixed(1)}
                    </p>
                  </div>

                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border font-mono ${getRatingBadge(
                      rating
                    )}`}
                  >
                    {rating}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-5 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
        <span className="text-[11px] text-gray-400">
          Ranked across 5 pillars: Attention, Interaction, Pickup, Conversion, Loyalty
        </span>
        {onNavigateScoring && (
          <button
            onClick={onNavigateScoring}
            className="text-xs text-amber-400 hover:text-amber-300 font-medium transition-colors"
          >
            Full Scorecards →
          </button>
        )}
      </div>
    </div>
  );
}
