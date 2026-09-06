/**
 * RetailAnalystDashboard – Consumer science & behavioral intelligence.
 * Sections: Consumer Behavior Analytics, Attention Heatmaps,
 * Product Attractiveness Reports, Customer Journey Analytics.
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

/* ─── Horizontal bar ───────────────────────────────────────── */
function BarSegment({ label, pct, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-300 w-40 truncate">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2.5 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-12 text-right">{pct}%</span>
    </div>
  );
}

/* ─── Funnel step ──────────────────────────────────────────── */
function FunnelStep({ stage, count, pct, isLast }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-white">{stage}</span>
          <span className="text-xs font-mono text-gray-400">{count?.toLocaleString()} ({pct}%)</span>
        </div>
        <div className="bg-gray-800 rounded-full h-2 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500" style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
      </div>
      {!isLast && <span className="text-gray-600 text-lg">→</span>}
    </div>
  );
}

const ARCHETYPE_COLORS = {
  Explorer: "bg-violet-500",
  "Quick Buyer": "bg-emerald-500",
  "Comparison Shopper": "bg-amber-500",
  "Impulse Buyer": "bg-pink-500",
  "Brand Loyal": "bg-cyan-500",
};

export default function RetailAnalystDashboard({ analytics, loading }) {
  const ra = analytics?.retail_analyst || {};
  const archetypes = ra.archetypes || {};
  const heatmap = ra.heatmap_summary || {};
  const attr = ra.attractiveness || {};
  const funnel = ra.funnel || {};
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const distribution = archetypes.distribution || {};
  const totalClassified = archetypes.total_classified || 1;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── 1. Consumer Behavior Analytics ──────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🧬</span> Consumer Behavior Analytics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <KpiCard icon="👥" label="Dominant Archetype" value={archetypes.dominant_segment || "Explorer"} sub={`${totalClassified} shoppers classified`} color="text-violet-400" />
          <div className="md:col-span-2 bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-3">Archetype Distribution</p>
            <div className="space-y-2.5">
              {Object.entries(distribution).map(([name, count]) => (
                <BarSegment
                  key={name}
                  label={name}
                  pct={Math.round((count / totalClassified) * 100)}
                  color={ARCHETYPE_COLORS[name] || "bg-gray-500"}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. Attention Heatmaps ──────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🗺️</span> Attention Heatmaps
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <KpiCard icon="📍" label="Total Zones" value={heatmap.total_zones || 0} />
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-2">🔥 Hotspot Zones</p>
            {(heatmap.hotspot_zones || []).length > 0 ? (
              <div className="space-y-1">
                {heatmap.hotspot_zones.map((z, i) => (
                  <span key={i} className="inline-flex mr-2 px-2 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{z}</span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500">No hotspot data</p>
            )}
          </div>
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-2">❄️ Dead Zones</p>
            {(heatmap.dead_zones || []).length > 0 ? (
              <div className="space-y-1">
                {heatmap.dead_zones.map((z, i) => (
                  <span key={i} className="inline-flex mr-2 px-2 py-0.5 rounded-lg text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">{z}</span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500">No dead zones detected</p>
            )}
          </div>
        </div>
        <button
          onClick={() => navigate("/analytics")}
          className="mt-3 text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors"
        >
          Open Heatmap Studio →
        </button>
      </section>

      {/* ── 3. Product Attractiveness Reports ──────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>⭐</span> Product Attractiveness Reports
        </h2>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <KpiCard icon="📊" label="Avg Attractiveness" value={`${attr.avg_score || 0} / 100`} sub={`Rating: ${attr.rating || "—"}`} color="text-amber-400" />
          <KpiCard icon="🏆" label="Top Performer" value={attr.top_performers?.[0]?.product_name || "—"} sub={`Score: ${attr.top_performers?.[0]?.attractiveness_score || "—"}`} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Top performers */}
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider mb-3">🟢 Top Attractors</p>
            <div className="space-y-2">
              {(attr.top_performers || []).map((p, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-white font-medium truncate mr-2">{p.product_name}</span>
                  <span className="font-mono text-emerald-400 font-bold">{p.attractiveness_score}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Attention leaks */}
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
            <p className="text-[10px] uppercase font-bold text-rose-400 tracking-wider mb-3">🔴 Attention Leaks</p>
            <div className="space-y-2">
              {(attr.attention_leaks || []).map((p, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-white font-medium truncate mr-2">{p.product_name}</span>
                  <span className="font-mono text-rose-400 font-bold">{p.attractiveness_score}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. Customer Journey Analytics ───────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🔻</span> Customer Journey Analytics — 4-Stage Funnel
        </h2>
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
          <div className="space-y-4">
            <FunnelStep stage="1. Browsed (Passersby)" count={funnel.passersby?.count} pct={funnel.passersby?.pct || 100} />
            <FunnelStep stage="2. Approached (Gaze/Dwell)" count={funnel.gaze_dwell?.count} pct={funnel.gaze_dwell?.pct || 0} />
            <FunnelStep stage="3. Interacted (Pickup)" count={funnel.physical_pickup?.count} pct={funnel.physical_pickup?.pct || 0} />
            <FunnelStep stage="4. Purchased" count={funnel.purchase_conversion?.count} pct={funnel.purchase_conversion?.pct || 0} isLast />
          </div>
        </div>
      </section>
    </div>
  );
}
