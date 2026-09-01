import React from 'react';

export function ScoreBadge({ score }) {
  const num = typeof score === "number" ? score : parseFloat(score) || 0;
  let color = "text-gray-400 bg-gray-500/10 border-gray-500/20";
  if (num >= 70) {
    color = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  } else if (num >= 40) {
    color = "text-amber-400 bg-amber-500/10 border-amber-500/20";
  } else if (num > 0) {
    color = "text-cyan-400 bg-cyan-500/10 border-cyan-500/20";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-semibold font-mono border ${color}`}
    >
      {num.toFixed(1)} / 100
    </span>
  );
}

export function DirectionBadge({ direction }) {
  const map = {
    LEFT: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
    RIGHT: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    CENTER: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    UP: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    DOWN: "bg-purple-500/10 text-purple-300 border-purple-500/20",
    UNKNOWN: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono border ${
        map[direction] || map.UNKNOWN
      }`}
    >
      {direction || "UNKNOWN"}
    </span>
  );
}

export function EventTypeBadge({ type }) {
  const map = {
    SHELF_ATTENTION: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    HEAD_POSE_ATTENTION: "bg-blue-500/10 text-blue-300 border-blue-500/20",
    PRODUCT_VIEWED: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    PRODUCT_PICKED_UP: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    PRODUCT_RETURNED: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    PRODUCT_PURCHASED: "bg-purple-500/10 text-purple-300 border-purple-500/20",
    PRODUCT_COMPARED: "bg-violet-500/10 text-violet-300 border-violet-500/20",
    TRACK_SESSION: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
  };

  const icons = {
    SHELF_ATTENTION: "👀",
    HEAD_POSE_ATTENTION: "🧭",
    PRODUCT_VIEWED: "👁️",
    PRODUCT_PICKED_UP: "🖐️",
    PRODUCT_RETURNED: "🔄",
    PRODUCT_PURCHASED: "💳",
    PRODUCT_COMPARED: "⚖️",
    TRACK_SESSION: "🚶",
  };

  const cleanType = (type || "").replace("PRODUCT_", "").replace("_", " ");

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[11px] font-medium border ${
        map[type] || "bg-gray-500/10 text-gray-400 border-gray-500/20"
      }`}
    >
      <span>{icons[type] || "📌"}</span>
      <span>{cleanType}</span>
    </span>
  );
}

export function MetricCard({ label, value, icon, gradient, subtitle, badge }) {
  return (
    <div className="bg-gray-900/70 backdrop-blur-xl border border-gray-800/60 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-gray-700/60 transition-all shadow-lg shadow-black/20">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-lg opacity-90`}
        >
          {icon}
        </div>
      </div>
      <div>
        <div className="flex items-baseline gap-2">
          <p className="text-2xl font-bold text-white tracking-tight">{value ?? "—"}</p>
          {badge && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 font-mono border border-gray-700/50">
              {badge}
            </span>
          )}
        </div>
        {subtitle && <p className="text-[11px] text-gray-400 mt-1">{subtitle}</p>}
      </div>
    </div>
  );
}
