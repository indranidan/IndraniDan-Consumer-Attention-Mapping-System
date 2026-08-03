/**
 * FilterPanel Component
 * ======================
 * Reusable collapsible filter panel with support for text, select, and number inputs.
 * Designed to sit between the search bar and data table.
 */

import { useState } from "react";

export default function FilterPanel({
  filters = [],
  values = {},
  onChange,
  onReset,
}) {
  const [open, setOpen] = useState(false);

  const activeCount = Object.values(values).filter(
    (v) => v !== "" && v !== null && v !== undefined
  ).length;

  return (
    <div className="border-b border-gray-800/50">
      {/* Toggle Button */}
      <div className="px-5 py-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 hover:text-white transition-all"
          id="filter-toggle-btn"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          Filters
          {activeCount > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-violet-500/20 text-xs font-semibold text-violet-400">
              {activeCount}
            </span>
          )}
          <svg
            className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all"
            id="filter-reset-btn"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reset Filters
          </button>
        )}
      </div>

      {/* Filter Fields — Collapsible */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          open ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-5 pb-4 pt-1">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {filters.map((filter) => (
              <div key={filter.key} className="space-y-1">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {filter.label}
                </label>

                {filter.type === "select" ? (
                  <select
                    value={values[filter.key] || ""}
                    onChange={(e) => onChange(filter.key, e.target.value)}
                    className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all"
                    id={`filter-${filter.key}`}
                  >
                    <option value="">{filter.placeholder || "All"}</option>
                    {(filter.options || []).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : filter.type === "number" ? (
                  <input
                    type="number"
                    value={values[filter.key] || ""}
                    onChange={(e) => onChange(filter.key, e.target.value)}
                    placeholder={filter.placeholder || ""}
                    min={filter.min}
                    step={filter.step || "any"}
                    className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all"
                    id={`filter-${filter.key}`}
                  />
                ) : (
                  <input
                    type="text"
                    value={values[filter.key] || ""}
                    onChange={(e) => onChange(filter.key, e.target.value)}
                    placeholder={filter.placeholder || ""}
                    className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all"
                    id={`filter-${filter.key}`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
