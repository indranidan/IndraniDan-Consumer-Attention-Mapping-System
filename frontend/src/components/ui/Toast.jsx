/**
 * Toast Notification Component
 * ============================
 * Floating, non-intrusive animated status alerts.
 */

import React from "react";

export default function Toast({ toasts = [], onDismiss }) {
  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const isSuccess = toast.type === "success";
        const isError = toast.type === "error";
        const isInfo = toast.type === "info";

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start justify-between gap-3 p-4 rounded-2xl border backdrop-blur-2xl shadow-2xl animate-fade-in transition-all duration-300 ${
              isSuccess
                ? "bg-emerald-950/90 border-emerald-500/30 text-emerald-100 shadow-emerald-950/50"
                : isError
                ? "bg-red-950/90 border-red-500/30 text-red-100 shadow-red-950/50"
                : "bg-gray-900/90 border-gray-700/50 text-white shadow-black/50"
            }`}
          >
            <div className="flex items-start gap-2.5">
              <span className="text-base flex-shrink-0 mt-0.5">
                {isSuccess ? "✓" : isError ? "⚠️" : "ℹ️"}
              </span>
              <div>
                {toast.title && <p className="text-xs font-bold leading-tight">{toast.title}</p>}
                <p className="text-xs text-gray-300 mt-0.5 leading-normal">{toast.message}</p>
              </div>
            </div>

            <button
              onClick={() => onDismiss && onDismiss(toast.id)}
              className="text-gray-400 hover:text-white transition-colors text-xs p-1"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
