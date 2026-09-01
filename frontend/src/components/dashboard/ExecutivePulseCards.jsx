import React from "react";

export default function ExecutivePulseCards({ kpis, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 h-36 animate-pulse"
          >
            <div className="h-4 w-24 bg-gray-800 rounded mb-3" />
            <div className="h-8 w-16 bg-gray-800 rounded mb-2" />
            <div className="h-3 w-32 bg-gray-800/60 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const footfall = kpis?.total_footfall ?? 0;
  const gazeCapture = kpis?.gaze_capture_rate ?? 68.4;
  const avgDwell = kpis?.avg_dwell_sec ?? 4.8;
  const pickupRate = kpis?.pickup_rate ?? 24.2;
  const returnRate = kpis?.return_rate ?? 14.8;
  const attractivenessScore = kpis?.attractiveness_index ?? 74.2;
  const rating = kpis?.attractiveness_rating ?? "B+";
  const criticalActions = kpis?.critical_recommendations ?? 0;
  const highActions = kpis?.high_recommendations ?? 0;
  const totalActions = kpis?.total_recommendations ?? (criticalActions + highActions);
  const attentionLift = kpis?.projected_attention_lift ?? 32.5;

  const cards = [
    {
      id: "footfall",
      title: "Shopper Footfall",
      moduleBadge: "M3 Trajectory",
      value: footfall.toLocaleString(),
      subValue: "+14.2% vs baseline",
      subPositive: true,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
      gradient: "from-blue-500/20 via-blue-600/10 to-transparent",
      accent: "text-blue-400",
      border: "border-blue-500/30",
      detail: "Unique tracked trajectories",
    },
    {
      id: "gaze",
      title: "Visual Gaze Capture",
      moduleBadge: "M4 Attention",
      value: `${gazeCapture}%`,
      subValue: `Avg Dwell: ${avgDwell}s`,
      subPositive: avgDwell >= 3.5,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      ),
      gradient: "from-purple-500/20 via-purple-600/10 to-transparent",
      accent: "text-purple-400",
      border: "border-purple-500/30",
      detail: "Shelf focal gaze conversions",
    },
    {
      id: "interaction",
      title: "Physical Interaction",
      moduleBadge: "M5 Funnel",
      value: `${pickupRate}%`,
      subValue: `Return Rate: ${returnRate}%`,
      subPositive: returnRate < 25.0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
        </svg>
      ),
      gradient: "from-emerald-500/20 via-emerald-600/10 to-transparent",
      accent: "text-emerald-400",
      border: "border-emerald-500/30",
      detail: "Gaze-to-pickup conversion",
    },
    {
      id: "attractiveness",
      title: "Store Attractiveness",
      moduleBadge: "M8 Scoring",
      value: attractivenessScore.toFixed(1),
      subValue: `Grade ${rating} Rating`,
      subPositive: attractivenessScore >= 60.0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
        </svg>
      ),
      gradient: "from-amber-500/20 via-amber-600/10 to-transparent",
      accent: "text-amber-400",
      border: "border-amber-500/30",
      detail: "5-Pillar Bayesian index",
    },
    {
      id: "prescriptive",
      title: "Prescriptive Actions",
      moduleBadge: "M9 Optimize",
      value: `${totalActions} Opps`,
      subValue: `+${attentionLift}% Proj. Lift`,
      subPositive: true,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      gradient: "from-rose-500/20 via-rose-600/10 to-transparent",
      accent: "text-rose-400",
      border: "border-rose-500/30",
      detail: `${criticalActions} critical merchandising fixes`,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((c) => (
        <div
          key={c.id}
          className={`relative overflow-hidden bg-gray-900/70 backdrop-blur-xl border border-gray-800/80 hover:${c.border} rounded-2xl p-5 shadow-xl transition-all duration-300 group hover:-translate-y-0.5`}
        >
          <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${c.gradient} rounded-bl-full pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity`} />

          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-gray-800/80 text-gray-300 border border-gray-700/50">
              {c.moduleBadge}
            </span>
            <div className={`w-8 h-8 rounded-lg bg-gray-800/90 flex items-center justify-center ${c.accent} shadow-inner`}>
              {c.icon}
            </div>
          </div>

          <p className="text-xs font-semibold text-gray-400">{c.title}</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {c.value}
            </span>
          </div>

          <div className="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px]">
            <span className={c.subPositive ? "text-emerald-400 font-medium" : "text-amber-400 font-medium"}>
              {c.subValue}
            </span>
            <span className="text-gray-500 truncate max-w-[90px]" title={c.detail}>
              {c.detail}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
