import React from "react";

export default function ConversionFunnelWidget({ funnel, loading, onNavigateJobs }) {
  if (loading) {
    return (
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl h-80 animate-pulse flex flex-col justify-between">
        <div className="h-5 w-48 bg-gray-800 rounded" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-gray-800/60 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const passersby = funnel?.passersby?.count ?? 1420;
  const gaze = funnel?.gaze_dwell?.count ?? 971;
  const pickups = funnel?.physical_pickup?.count ?? 344;
  const purchases = funnel?.purchase_conversion?.count ?? 256;

  const gazePct = passersby > 0 ? ((gaze / passersby) * 100).toFixed(1) : "0.0";
  const pickupPct = gaze > 0 ? ((pickups / gaze) * 100).toFixed(1) : "0.0";
  const purchasePct = pickups > 0 ? ((purchases / pickups) * 100).toFixed(1) : "0.0";
  const endToEndPct = passersby > 0 ? ((purchases / passersby) * 100).toFixed(1) : "0.0";

  const stages = [
    {
      id: "passersby",
      label: "1. Zone Passersby",
      count: passersby,
      sharePct: "100%",
      subLabel: "Total Foot Traffic",
      gradient: "from-blue-500 to-indigo-600",
      bgBar: "bg-blue-500",
      widthPct: 100,
      dropoff: `${(100 - parseFloat(gazePct)).toFixed(1)}% Gaze Blindness`,
    },
    {
      id: "gaze",
      label: "2. Gaze Dwell (≥1.5s)",
      count: gaze,
      sharePct: `${gazePct}% of traffic`,
      subLabel: "Visual Hook Capture",
      gradient: "from-purple-500 to-violet-600",
      bgBar: "bg-purple-500",
      widthPct: Math.max(15, parseFloat(gazePct)),
      dropoff: `${(100 - parseFloat(pickupPct)).toFixed(1)}% Touch Hesitation`,
    },
    {
      id: "pickup",
      label: "3. Physical Pickup",
      count: pickups,
      sharePct: `${pickupPct}% of viewers`,
      subLabel: "Product Interaction",
      gradient: "from-emerald-500 to-teal-600",
      bgBar: "bg-emerald-500",
      widthPct: Math.max(12, (pickups / passersby) * 100),
      dropoff: `${(100 - parseFloat(purchasePct)).toFixed(1)}% Return / Drop`,
    },
    {
      id: "purchase",
      label: "4. Purchase Conversion",
      count: purchases,
      sharePct: `${endToEndPct}% End-to-End`,
      subLabel: "Checkout Basket Yield",
      gradient: "from-amber-500 to-rose-500",
      bgBar: "bg-amber-500",
      widthPct: Math.max(10, (purchases / passersby) * 100),
      dropoff: null,
    },
  ];

  return (
    <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🚶</span> 4-Stage Shopper Conversion Funnel
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Consumer funnel transition efficiency from footfall to checkout
            </p>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20 font-mono">
            Modules 3–6
          </span>
        </div>

        <div className="space-y-3.5 mt-4">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="relative">
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-200">{stage.label}</span>
                  <span className="text-[10px] text-gray-500">({stage.subLabel})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-white font-bold">{stage.count.toLocaleString()}</span>
                  <span className="text-[10px] text-gray-400 font-mono">[{stage.sharePct}]</span>
                </div>
              </div>

              {/* Progress Bar Container */}
              <div className="h-4 bg-gray-800/60 rounded-lg overflow-hidden relative p-0.5 border border-gray-700/30">
                <div
                  className={`h-full rounded-md bg-gradient-to-r ${stage.gradient} transition-all duration-700`}
                  style={{ width: `${stage.widthPct}%` }}
                />
              </div>

              {/* Drop-off connector */}
              {stage.dropoff && (
                <div className="flex items-center gap-1 text-[10px] text-rose-400/80 mt-0.5 pl-2 font-mono">
                  <span>↳ Drop-off:</span>
                  <span className="font-medium">{stage.dropoff}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
        <div className="text-[11px] text-gray-400">
          Full Pipeline Yield:{" "}
          <span className="font-bold text-amber-400 font-mono">{endToEndPct}%</span>
        </div>
        {onNavigateJobs && (
          <button
            onClick={onNavigateJobs}
            className="text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors"
          >
            Inspect AI Jobs →
          </button>
        )}
      </div>
    </div>
  );
}
