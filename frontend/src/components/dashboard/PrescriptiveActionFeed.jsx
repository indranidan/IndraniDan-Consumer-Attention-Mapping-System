import React from "react";

export default function PrescriptiveActionFeed({
  recommendations,
  loading,
  onOpenSimulator,
  onNavigateRecommendations,
}) {
  if (loading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl h-80 animate-pulse flex flex-col justify-between">
        <div className="h-5 w-48 bg-gray-800 rounded" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-800/60 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const recList = recommendations || [];

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30 font-bold animate-pulse";
      case "HIGH":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30 font-semibold";
      case "MEDIUM":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      default:
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case "SHELF_OPTIMIZATION":
        return "📐";
      case "PRODUCT_PLACEMENT":
        return "🔄";
      case "PROMOTIONAL_PLACEMENT":
        return "🏷️";
      case "CONSUMER_ENGAGEMENT":
        return "🛍️";
      case "LAYOUT_IMPROVEMENT":
        return "🗺️";
      default:
        return "💡";
    }
  };

  return (
    <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>💡</span> Prescriptive AI Merchandising Actions
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Targeted planogram, shelf tier, and promotional interventions
            </p>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 font-mono">
            Module 9
          </span>
        </div>

        {recList.length === 0 ? (
          <div className="p-8 text-center text-gray-400 bg-gray-800/30 rounded-xl border border-gray-800">
            <p className="text-sm font-semibold text-white">All Fixtures Optimized</p>
            <p className="text-xs text-gray-500 mt-1">
              No critical merchandising anomalies detected in the current scope.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {recList.slice(0, 4).map((rec) => {
              const attLift = rec.expected_impact?.attention_lift_pct ?? 25.0;
              const convLift = rec.expected_impact?.conversion_lift_pct ?? 10.0;

              return (
                <div
                  key={rec.id}
                  className="p-3.5 rounded-xl bg-gray-800/40 hover:bg-gray-800/70 border border-gray-700/40 transition-all group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider ${getPriorityBadge(
                            rec.priority
                          )}`}
                        >
                          {rec.priority}
                        </span>
                        <span className="text-[11px] text-gray-400 font-medium flex items-center gap-1">
                          <span>{getCategoryIcon(rec.category)}</span>
                          {rec.category?.replace("_", " ")}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-white group-hover:text-violet-300 transition-colors">
                        {rec.title}
                      </h4>
                      <p className="text-[11px] text-gray-400 mt-1 leading-relaxed line-clamp-2">
                        {rec.proposed_action || rec.description}
                      </p>
                    </div>

                    {/* Projected Impact Pill */}
                    <div className="text-right shrink-0 flex flex-col items-end gap-1">
                      <div className="px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-mono font-bold">
                        +{attLift}% Attn
                      </div>
                      {rec.shelf_swap_details && onOpenSimulator && (
                        <button
                          onClick={() => onOpenSimulator(rec)}
                          className="text-[10px] text-violet-400 hover:text-violet-300 font-semibold underline mt-1"
                        >
                          Simulate →
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-5 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
        <span className="text-[11px] text-gray-400">
          Ranked by Composite Attention & Conversion ROI Lift Score
        </span>
        {onNavigateRecommendations && (
          <button
            onClick={onNavigateRecommendations}
            className="text-xs text-rose-400 hover:text-rose-300 font-medium transition-colors"
          >
            All Recommendations ({recList.length}) →
          </button>
        )}
      </div>
    </div>
  );
}
