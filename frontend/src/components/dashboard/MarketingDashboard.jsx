/**
 * MarketingDashboard – Campaign & merchandising command center.
 * Sections: Campaign Effectiveness, Product Visibility Analytics,
 * Promotional Performance, Customer Engagement Metrics.
 */
import React from "react";
import { useNavigate } from "react-router-dom";

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
  const navigate = useNavigate();

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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon="👁️" label="Eye-Level Lift" value={`+${campaign.eye_level_engagement_lift || 0}%`} sub="Visual priority score" color="text-violet-400" />
          <KpiCard icon="🎯" label="Endcap Conversion" value={`+${campaign.endcap_conversion_increase || 0}%`} sub="Promotional endcap lift" color="text-emerald-400" />
          <KpiCard icon="⚡" label="Promo Response" value={`${campaign.promo_response_rate || 0}%`} sub="Shoppers engaging promos" />
          <KpiCard icon="✨" label="Top Campaign" value={campaign.top_performing_campaign || "N/A"} sub="Highest engagement" />
        </div>
      </section>

      {/* ── 2. Product Visibility Analytics ────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>👁️</span> Product Visibility by Category
        </h2>
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
          <div className="space-y-3">
            {Object.entries(categoryGaze).length === 0 && (
              <p className="text-xs text-gray-500 text-center py-4">No category visibility data available</p>
            )}
            {Object.entries(categoryGaze).map(([cat, pct], idx) => (
              <BarSegment key={cat} label={cat} pct={pct} color={CATEGORY_COLORS[idx % CATEGORY_COLORS.length]} />
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-gray-800 flex justify-between text-[11px] text-gray-400">
            <span>Blind Spots: <strong className="text-rose-400">{visibility.blind_spot_zones?.join(", ") || "None"}</strong></span>
            <span>Premium Dwell: <strong className="text-violet-400">{visibility.premium_shelf_dwell_share || 0}%</strong></span>
          </div>
        </div>
      </section>

      {/* ── 3. Promotional Performance ─────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🏷️</span> Promotional Fixture Performance
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon="🏷️" label="Active Promos" value={promo.active_promotions || 0} sub="Currently running" />
          <KpiCard icon="🛒" label="Promo Pickups" value={promo.promo_product_pickups || 0} sub="Items selected" color="text-emerald-400" />
          <KpiCard icon="⏱️" label="Dwell/Promo" value={`${promo.dwell_per_promo_sec || 0}s`} sub="Average attention span" />
          <KpiCard icon="⭐" label="Endcap vs Aisle" value={`${promo.endcap_vs_aisle_ratio || 0}x`} sub="Endcap efficiency multiple" color="text-amber-400" />
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
            onClick={() => navigate("/recommendations")}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-violet-600/20 transition-all hover:scale-[1.02] cursor-pointer"
          >
            <span>💡</span> View Actionable Merchandising Recommendations
          </button>
        </div>
      </section>
    </div>
  );
}
