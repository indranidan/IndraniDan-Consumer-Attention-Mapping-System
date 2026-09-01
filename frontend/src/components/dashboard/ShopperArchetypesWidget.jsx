import React from "react";

export default function ShopperArchetypesWidget({ archetypes, loading, onNavigateBehavior }) {
  if (loading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl h-80 animate-pulse flex flex-col justify-between">
        <div className="h-5 w-48 bg-gray-800 rounded" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 bg-gray-800/60 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const dominant = archetypes?.dominant_segment || "Explorer";
  const rawDist = archetypes?.distribution || {
    Explorer: 38,
    "Quick Buyer": 27,
    "Comparison Shopper": 20,
    "Brand Loyal": 15,
  };
  const total = Object.values(rawDist).reduce((sum, v) => sum + v, 0) || 100;

  const segmentConfig = {
    Explorer: {
      icon: "🧭",
      label: "Explorer Shoppers",
      gradient: "from-blue-500 to-indigo-600",
      bgBar: "bg-blue-500",
      description: "Broad store exploration with high dwell-to-transit ratio. Target with cross-category impulse displays.",
    },
    "Quick Buyer": {
      icon: "⚡",
      label: "Quick Buyers",
      gradient: "from-amber-500 to-orange-600",
      bgBar: "bg-amber-500",
      description: "Fast-moving target seekers with high path efficiency. Maintain clear eye-level staple product visibility.",
    },
    "Comparison Shopper": {
      icon: "🔍",
      label: "Comparison Shoppers",
      gradient: "from-purple-500 to-pink-600",
      bgBar: "bg-purple-500",
      description: "Evaluators with high gaze alternation rates. Optimize side-by-side spec comparison and shelf pricing.",
    },
    "Brand Loyal": {
      icon: "💎",
      label: "Brand Loyalists",
      gradient: "from-emerald-500 to-teal-600",
      bgBar: "bg-emerald-500",
      description: "High brand-block concentration. Maximize facing density for anchor market leaders.",
    },
    "Impulse Buyer": {
      icon: "✨",
      label: "Impulse Buyers",
      gradient: "from-rose-500 to-red-600",
      bgBar: "bg-rose-500",
      description: "Rapid uncalculated pickups triggered by endcap wobblers and promotional lighting.",
    },
  };

  const segments = Object.entries(rawDist).map(([key, count]) => {
    const normKey = key.replace("_", " ");
    const cfg = segmentConfig[normKey] || segmentConfig[key] || {
      icon: "👤",
      label: normKey,
      gradient: "from-gray-500 to-gray-600",
      bgBar: "bg-gray-500",
      description: "Shopper behavioral pattern across store aisles.",
    };
    const pct = ((count / total) * 100).toFixed(1);
    return {
      key: normKey,
      count,
      pct,
      ...cfg,
    };
  });

  const dominantInfo =
    segmentConfig[dominant.replace("_", " ")] || segmentConfig.Explorer;

  return (
    <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🧠</span> Shopper Behavior Archetypes
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Unsupervised trajectory clustering & decision style classification
            </p>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
            Module 6
          </span>
        </div>

        {/* Dominant Highlight Box */}
        <div className="p-3 rounded-xl bg-gray-800/50 border border-gray-700/40 mb-4 flex items-start gap-3">
          <div className="text-2xl">{dominantInfo.icon}</div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Dominant: {dominantInfo.label}
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5 leading-relaxed">
              {dominantInfo.description}
            </p>
          </div>
        </div>

        {/* Breakdown Progress Bars */}
        <div className="space-y-3">
          {segments.map((seg) => (
            <div key={seg.key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-gray-300 font-medium flex items-center gap-1.5">
                  <span>{seg.icon}</span> {seg.label}
                </span>
                <span className="font-mono text-white font-bold">{seg.pct}%</span>
              </div>
              <div className="h-2 bg-gray-800/80 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${seg.gradient} transition-all duration-700`}
                  style={{ width: `${seg.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
        <span className="text-[11px] text-gray-400">
          Total Analyzed Shoppers:{" "}
          <span className="font-mono text-cyan-400 font-bold">
            {archetypes?.total_classified || total}
          </span>
        </span>
        {onNavigateBehavior && (
          <button
            onClick={onNavigateBehavior}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
          >
            Trajectory Maps →
          </button>
        )}
      </div>
    </div>
  );
}
