/**
 * Planogram Swap Simulator
 * =========================
 * Interactive What-If simulation tool for store merchandisers.
 * Simulates the projected impact of moving SKUs between shelf tiers
 * and changing shelf facing allocations in real time.
 */

import { useState, useEffect } from "react";
import { simulatePlanogram } from "../../services/recommendationService";

const SHELF_TIERS = [
  { id: "TOP", label: "Top Tier (Stretch)", gamma: 0.70, color: "from-blue-500/20 to-blue-600/20 border-blue-500/30 text-blue-400" },
  { id: "EYE_LEVEL", label: "Eye-Level Tier (Premium)", gamma: 1.00, color: "from-emerald-500/20 to-emerald-600/20 border-emerald-500/30 text-emerald-400" },
  { id: "TOUCH", label: "Touch Tier (Chest/Mid)", gamma: 0.85, color: "from-cyan-500/20 to-cyan-600/20 border-cyan-500/30 text-cyan-400" },
  { id: "BOTTOM", label: "Bottom Tier (Stoop/Floor)", gamma: 0.40, color: "from-purple-500/20 to-purple-600/20 border-purple-500/30 text-purple-400" },
];

export default function PlanogramSwapSimulator({ initialProduct = null }) {
  const [productId, setProductId] = useState(initialProduct?.id || initialProduct?.product_id || "SKU-DEMO");
  const [productName, setProductName] = useState(initialProduct?.name || initialProduct?.product_name || "Selected Product");
  const [currentTier, setCurrentTier] = useState(initialProduct?.current_tier || "BOTTOM");
  const [targetTier, setTargetTier] = useState(initialProduct?.target_tier || "EYE_LEVEL");
  const [currentFacings, setCurrentFacings] = useState(1);
  const [targetFacings, setTargetFacings] = useState(2);
  const [baseAttractiveness, setBaseAttractiveness] = useState(
    initialProduct?.attractiveness_score || initialProduct?.score || 45.0
  );
  const [baseIntrinsic, setBaseIntrinsic] = useState(
    initialProduct?.intrinsic_score || 72.0
  );

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleSimulate = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = {
        product_id: productId,
        current_shelf_tier: currentTier,
        target_shelf_tier: targetTier,
        current_facing_count: Number(currentFacings) || 1,
        target_facing_count: Number(targetFacings) || 1,
        current_attractiveness_score: Number(baseAttractiveness) || 0.0,
        current_intrinsic_score: Number(baseIntrinsic) || 0.0,
      };
      const res = await simulatePlanogram(payload);
      setResult(res);
    } catch (err) {
      console.error("Simulation failed:", err);
      setError(err?.response?.data?.detail || "Failed to compute simulation projection");
    } finally {
      setLoading(false);
    }
  };

  // Run initial simulation on mount
  useEffect(() => {
    handleSimulate();
  }, [currentTier, targetTier, currentFacings, targetFacings, baseAttractiveness]);

  return (
    <div className="bg-gray-900/80 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between pb-5 border-b border-gray-800/60 mb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🔮</span>
            <h3 className="text-lg font-bold text-white tracking-wide">
              "What-If" Planogram Simulation Studio
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              REAL-TIME COUNTERFACTUAL
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Simulate shelf tier swaps, visibility multiplier changes, and facing elasticity with zero database side effects.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
          ⚠️ {error}
        </div>
      )}

      {/* Grid: Inputs vs Results */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Configuration Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-4 space-y-3.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              1. SKU & Baseline Properties
            </h4>
            
            <div>
              <label className="block text-[11px] font-medium text-gray-400 mb-1">
                Product Name / SKU
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-cyan-500/50"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                  Observed Score (0-100)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={baseAttractiveness}
                  onChange={(e) => setBaseAttractiveness(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                  Intrinsic Score (0-100)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={baseIntrinsic}
                  onChange={(e) => setBaseIntrinsic(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Tier Selection */}
          <div className="bg-gray-950/60 border border-gray-800/60 rounded-xl p-4 space-y-3.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              2. Shelf Tier Adjustment
            </h4>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                  Current Shelf Tier
                </label>
                <select
                  value={currentTier}
                  onChange={(e) => setCurrentTier(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50"
                >
                  {SHELF_TIERS.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label} (γ={t.gamma})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-cyan-400 mb-1">
                  Target Simulated Tier
                </label>
                <select
                  value={targetTier}
                  onChange={(e) => setTargetTier(e.target.value)}
                  className="w-full bg-gray-900 border border-cyan-500/40 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-400"
                >
                  {SHELF_TIERS.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label} (γ={t.gamma})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Facings */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                  Current Facings
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={currentFacings}
                  onChange={(e) => setCurrentFacings(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50 font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-cyan-400 mb-1">
                  Target Facings
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={targetFacings}
                  onChange={(e) => setTargetFacings(e.target.value)}
                  className="w-full bg-gray-900 border border-cyan-500/40 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Projected Impact Card (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-between">
          <div className="bg-gradient-to-br from-gray-950/90 via-gray-900/80 to-gray-950/90 border border-gray-800 rounded-xl p-5 space-y-5 h-full">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Simulation Projection Results
              </span>
              {result && (
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold font-mono border ${
                    result.is_improvement
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  }`}
                >
                  {result.is_improvement ? "▲ POSITIVE IMPACT" : "▼ NEGATIVE / NEUTRAL"}
                </span>
              )}
            </div>

            {/* Big Lift KPIs */}
            {result ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-900/90 border border-gray-800/80 rounded-xl p-4 text-center relative overflow-hidden">
                  <div className="text-[11px] text-gray-400 uppercase tracking-wider mb-1">
                    Projected Attention Lift
                  </div>
                  <div
                    className={`text-3xl font-extrabold font-mono ${
                      result.attention_lift_pct >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {result.attention_lift_pct >= 0 ? "+" : ""}
                    {result.attention_lift_pct}%
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1">
                    Gamma ratio {result.original_gamma} → {result.simulated_gamma}
                  </div>
                </div>

                <div className="bg-gray-900/90 border border-gray-800/80 rounded-xl p-4 text-center relative overflow-hidden">
                  <div className="text-[11px] text-gray-400 uppercase tracking-wider mb-1">
                    Projected Conversion Lift
                  </div>
                  <div
                    className={`text-3xl font-extrabold font-mono ${
                      result.conversion_lift_pct >= 0 ? "text-cyan-400" : "text-red-400"
                    }`}
                  >
                    {result.conversion_lift_pct >= 0 ? "+" : ""}
                    {result.conversion_lift_pct}%
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1">
                    Estimated checkout yield
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 text-xs">
                Computing simulation projections...
              </div>
            )}

            {/* Score Comparison Bars */}
            {result && (
              <div className="space-y-3 bg-gray-900/50 p-4 rounded-xl border border-gray-800/50">
                {/* Attractiveness Score Bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400">Attractiveness Score</span>
                    <span className="font-mono text-gray-300">
                      {result.original_attractiveness_score} →{" "}
                      <span className="text-emerald-400 font-bold">
                        {result.simulated_attractiveness_score}
                      </span>
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2.5 relative overflow-hidden">
                    <div
                      className="bg-gray-600 h-2.5 rounded-full absolute left-0"
                      style={{ width: `${Math.min(100, result.original_attractiveness_score)}%` }}
                    />
                    <div
                      className="bg-emerald-500 h-2.5 rounded-full opacity-70"
                      style={{ width: `${Math.min(100, result.simulated_attractiveness_score)}%` }}
                    />
                  </div>
                </div>

                {/* Shelf Visibility Score Bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400">Shelf Visibility Index</span>
                    <span className="font-mono text-gray-300">
                      {result.original_visibility_score} →{" "}
                      <span className="text-cyan-400 font-bold">
                        {result.simulated_visibility_score}
                      </span>
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2.5 relative overflow-hidden">
                    <div
                      className="bg-gray-600 h-2.5 rounded-full absolute left-0"
                      style={{ width: `${Math.min(100, result.original_visibility_score)}%` }}
                    />
                    <div
                      className="bg-cyan-500 h-2.5 rounded-full opacity-70"
                      style={{ width: `${Math.min(100, result.simulated_visibility_score)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Summary Rationale Box */}
            {result && (
              <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl text-xs text-cyan-300/90 leading-relaxed">
                💡 <strong>Simulation Insight:</strong> Moving from{" "}
                <span className="text-white font-semibold">{result.original_tier}</span> (γ={result.original_gamma}) to{" "}
                <span className="text-white font-semibold">{result.simulated_tier}</span> (γ={result.simulated_gamma}) with{" "}
                <span className="text-white font-semibold">{targetFacings} facing(s)</span> is projected to generate a{" "}
                <span className="text-emerald-400 font-bold">{result.attention_lift_pct}%</span> net attention lift.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
