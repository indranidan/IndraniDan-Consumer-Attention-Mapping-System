/**
 * StoreManagerDashboard – Minimal operational floor dashboard.
 * Sections: Store Traffic Analytics, Product Engagement Insights,
 * Shelf Performance Reports, Conversion Metrics.
 */
import React from "react";

/* ─── Reusable KPI card ────────────────────────────────────── */
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

/* ─── Status badge ─────────────────────────────────────────── */
function StatusBadge({ status }) {
  const styles = {
    Optimal: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    "Low Dwell": "bg-amber-500/10 text-amber-400 border-amber-500/20",
    "Restock Check": "bg-rose-500/10 text-rose-400 border-rose-500/20",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${styles[status] || "bg-gray-500/10 text-gray-400"}`}>
      {status}
    </span>
  );
}

export default function StoreManagerDashboard({ analytics, stats, loading }) {
  const sm = analytics?.store_manager || {};
  const shelves = sm.shelf_performance || [];
  const frictionItems = sm.friction_watch || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── 1. Store Traffic Analytics ──────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🚶</span> Store Traffic Analytics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon="👥" label="Today's Footfall" value={sm.footfall?.toLocaleString() || "0"} />
          <KpiCard icon="👁️" label="Active Viewers" value={sm.active_visitors?.toLocaleString() || "0"} sub={`${analytics?.kpis?.gaze_capture_rate || 0}% gaze capture`} />
          <KpiCard icon="⏱️" label="Avg Dwell Time" value={`${sm.avg_dwell_sec || 0}s`} sub="Per shelf interaction" />
          <KpiCard icon="⏰" label="Peak Hour" value={sm.peak_hour || "—"} sub="Highest traffic window" />
        </div>
      </section>

      {/* ── 2. Product Engagement Insights ──────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>✋</span> Product Engagement Insights
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KpiCard icon="🤚" label="Total Pickups" value={sm.total_pickups?.toLocaleString() || "0"} />
          <KpiCard icon="📈" label="Touch Rate" value={`${sm.touch_rate || 0}%`} sub="% of viewers who touched" />
          <KpiCard icon="🔄" label="Return Rate" value={`${sm.return_rate || 0}%`} sub="Items put back" color={sm.return_rate > 20 ? "text-rose-400" : "text-white"} />
        </div>

        {frictionItems.length > 0 && (
          <div className="mt-4 bg-gray-900/40 border border-gray-800/80 rounded-2xl p-4">
            <h3 className="text-[11px] font-bold text-amber-400 uppercase tracking-wider mb-2">⚠️ Friction Watch — High Pickups, Low Buy</h3>
            <div className="space-y-2">
              {frictionItems.map((item, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-white font-medium">{item.product_name}</span>
                  <span className="text-gray-400">{item.pickups} pickups · {item.returns} returns · <span className="text-rose-400 font-bold">{item.return_rate}% return</span></span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── 3. Shelf Performance Reports ────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>📋</span> Shelf Performance Reports
        </h2>
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl overflow-hidden">
          {shelves.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400">
                    <th className="px-4 py-3 font-semibold">Shelf</th>
                    <th className="px-4 py-3 font-semibold">Store</th>
                    <th className="px-4 py-3 font-semibold">Score</th>
                    <th className="px-4 py-3 font-semibold">Viewers</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {shelves.map((s, i) => (
                    <tr key={i} className="hover:bg-gray-800/30 transition-colors">
                      <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                      <td className="px-4 py-3 text-gray-400">{s.store_name}</td>
                      <td className="px-4 py-3 font-mono text-white">{s.attention_score}</td>
                      <td className="px-4 py-3 text-gray-400">{s.viewers}</td>
                      <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500 text-xs">No shelf performance data available yet.</div>
          )}
        </div>
      </section>

      {/* ── 4. Conversion Metrics ───────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🛍️</span> Conversion Metrics
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <KpiCard icon="💰" label="Store Conversion Rate" value={`${sm.conversion_rate || 0}%`} sub="Of entrants who purchased" color="text-emerald-400" />
          <KpiCard icon="🧾" label="Total Transactions" value={sm.total_transactions?.toLocaleString() || "0"} sub="Completed purchases" />
        </div>
      </section>
    </div>
  );
}
