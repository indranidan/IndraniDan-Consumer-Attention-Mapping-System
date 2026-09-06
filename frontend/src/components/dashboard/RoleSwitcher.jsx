/**
 * RoleSwitcher – Minimal pill tab bar for Admin dashboard view switching.
 * Only visible to Administrator role users.
 */
import React from "react";

const ROLES = [
  { key: "Store Manager", icon: "🏪", label: "Store Manager" },
  { key: "Retail Analyst", icon: "📊", label: "Retail Analyst" },
  { key: "Marketing Manager", icon: "🎯", label: "Marketing" },
  { key: "Administrator", icon: "⚙️", label: "Admin" },
];

export default function RoleSwitcher({ activeRole, onSwitch }) {
  return (
    <div className="flex items-center gap-1 bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-1.5">
      {ROLES.map((r) => {
        const active = activeRole === r.key;
        return (
          <button
            key={r.key}
            onClick={() => onSwitch(r.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${
              active
                ? "bg-violet-600/90 text-white shadow-lg shadow-violet-600/20"
                : "text-gray-400 hover:text-white hover:bg-gray-800/60"
            }`}
          >
            <span className="text-sm">{r.icon}</span>
            <span className="hidden sm:inline">{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
