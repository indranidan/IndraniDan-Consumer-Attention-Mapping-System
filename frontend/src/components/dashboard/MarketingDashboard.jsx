/**
 * MarketingDashboard – Campaign & merchandising command center.
 * Sections: Campaign Effectiveness, Product Visibility Analytics,
 * Promotional Performance, Customer Engagement Metrics.
 */
import React, { useState } from "react";
import PlanogramSwapSimulator from "../recommendations/PlanogramSwapSimulator";

function KpiCard({ icon, label, value, sub, color = "text-white" }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
      <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1.5">
        <span>{icon}</span>{label}
      </p>
      <p className={`text-2xl font-extrabold mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function BarSegment({ label, pct, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-300 w-36 truncate">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2.5 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-12 text-right">{pct}%</span>
    </div>
  );
}

const CATEGORY_COLORS = [
  "bg-violet-500", "bg-emerald-500", "bg-amber-500", "bg-pink-500", "bg-cyan-500", "bg-indigo-500",
];

export default function MarketingDashboard({ analytics, loading }) {
  const mm = analytics?.marketing_manager || {};
  const campaign = mm.campaign_lift || {};
  const visibility = mm.visibility || {};
  const promo = mm.promotional_performance || {};
  const engagement = mm.engagement || {};
  const categoryGaze = visibility.category_gaze || {};

  const [simulatorOpen, setSimulatorOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── 1. Campaign Effectiveness ──────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🚀</span> Campaign Effectiveness
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <KpiCard
            icon="📈"
            label="Promotional Dwell Lift"
            value={`+${campaign.promotional_dwell_lift_pct || 0}%`}
            sub="vs baseline gaze duration"
            color="text-emerald-400"
          />
          <KpiCard
            icon="💎"
            label="Marketing ROI Index"
            value={campaign.marketing_roi_index || 0}
            sub="Composite campaign score"
            color="text-violet-400"
          />
        </div>
      </section>

      {/* ── 2. Product Visibility Analytics ─────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>👁️</span> Product Visibility Analytics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <KpiCard icon="🔝" label="Eye-Level Gaze Share" value={`${visibility.eye_level_share || 0}%`} sub="Of total shopper glances" color="text-emerald-400" />
          <KpiCard icon="⬇️" label="Bottom-Shelf Share" value={`${visibility.bottom_shelf_share || 0}%`} sub="Lower visibility zone" color="text-amber-400" />
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-3">📊 Category Attention Share</p>
            <div className="space-y-2.5">
              {Object.entries(categoryGaze).map(([cat, pct], i) => (
                <BarSegment key={cat} label={cat} pct={pct} color={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. Promotional Performance ──────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🎪</span> Promotional Performance
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <KpiCard icon="🏷️" label="End-Cap Engagement" value={`${promo.endcap_engagement_rate || 0}%`} sub="Display feature engagement" />
          <KpiCard icon="🤝" label="Promo Interaction Yield" value={`${promo.promo_interaction_yield || 0}%`} sub="Featured SKU pickup rate" />
        </div>
      </section>

      {/* ── 4. Customer Engagement Metrics ──────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>💡</span> Customer Engagement Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiCard icon="🔁" label="Repeat Engagement" value={`${engagement.repeat_engagement_rate || 0}%`} sub="Brand loyalty indicator" />
          <KpiCard icon="📋" label="Prescriptive Opps" value={engagement.total_recommendations || 0} sub="Merchandising actions" />
          <KpiCard icon="🔮" label="Projected Lift" value={`+${engagement.projected_attention_lift || 0}%`} sub="Attention improvement" color="text-violet-400" />
        </div>

        <div className="mt-4">
          <button
            onClick={() => setSimulatorOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-violet-600/20 transition-all hover:scale-[1.02]"
          >
            <span>🔮</span> Launch Planogram What-If Simulator
          </button>
        </div>
      </section>

      {/* ── Planogram Swap Simulator Modal ──────────────────────── */}
      {simulatorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          {/* Backdrop click to close */}
          <div className="absolute inset-0" onClick={() => setSimulatorOpen(false)} />
          <div className="bg-gray-900 border border-gray-800 rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative z-10">
            {/* Close button — prominent ✕ */}
            <button
              onClick={() => setSimulatorOpen(false)}
              className="absolute top-4 right-4 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-gray-800 hover:bg-rose-600 border border-gray-700 hover:border-rose-500 text-gray-400 hover:text-white transition-all duration-200 shadow-lg"
              aria-label="Close simulator"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <PlanogramSwapSimulator />
          </div>
        </div>
      )}
    </div>
  );
}
