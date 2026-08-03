/**
 * DataTable Component
 * ====================
 * Reusable table with search bar, loading skeleton, empty state, and server-side pagination.
 */

export default function DataTable({
  columns,
  data,
  loading,
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search...",
  renderRow,
  emptyIcon,
  emptyTitle = "No data found",
  emptyDescription = "Try adjusting your search or create a new entry.",
  filterSlot,
  // Pagination props
  page = 1,
  pageSize = 10,
  totalCount = 0,
  onPageChange,
  onPageSizeChange,
}) {
  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const startItem = totalCount > 0 ? (page - 1) * pageSize + 1 : 0;
  const endItem = Math.min(page * pageSize, totalCount);

  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl overflow-hidden">
      {/* Search Bar */}
      <div className="px-5 py-4 border-b border-gray-800/50">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full pl-10 pr-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all"
          />
        </div>
      </div>

      {/* Filter Panel Slot */}
      {filterSlot}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800/50">
              {columns.map((col, i) => (
                <th
                  key={i}
                  className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/30">
            {loading ? (
              // Loading skeleton
              Array.from({ length: pageSize > 10 ? 10 : pageSize }).map((_, i) => (
                <tr key={i}>
                  {columns.map((_, j) => (
                    <td key={j} className="px-5 py-4">
                      <div className="h-4 bg-gray-800/50 rounded-lg animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              // Empty state
              <tr>
                <td colSpan={columns.length} className="px-5 py-16 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-2xl bg-gray-800/50 flex items-center justify-center text-gray-600">
                      {emptyIcon || (
                        <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                          />
                        </svg>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-400">{emptyTitle}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{emptyDescription}</p>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              data.map(renderRow)
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {onPageChange && (
        <div className="px-5 py-3 border-t border-gray-800/50 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-400">
          <div className="flex items-center gap-4">
            {/* Page Size Selector Dropdown */}
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Rows per page:</span>
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange && onPageSizeChange(Number(e.target.value))}
                className="px-2.5 py-1.5 bg-gray-800/60 border border-gray-700/50 rounded-lg text-white font-medium focus:outline-none focus:border-violet-500/50"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            {/* Showing Range Summary */}
            <span>
              Showing <strong className="text-white font-medium">{startItem}</strong> to{" "}
              <strong className="text-white font-medium">{endItem}</strong> of{" "}
              <strong className="text-white font-medium">{totalCount}</strong> results
            </span>
          </div>

          {/* Page Navigation Controls */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={page <= 1 || loading}
              onClick={() => onPageChange(page - 1)}
              className="px-3 py-1.5 rounded-lg bg-gray-800/60 border border-gray-700/50 text-gray-300 hover:text-white hover:bg-gray-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Prev
            </button>

            <span className="px-3 py-1.5 text-gray-300 font-medium">
              Page {page} of {totalPages}
            </span>

            <button
              type="button"
              disabled={page >= totalPages || loading}
              onClick={() => onPageChange(page + 1)}
              className="px-3 py-1.5 rounded-lg bg-gray-800/60 border border-gray-700/50 text-gray-300 hover:text-white hover:bg-gray-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1"
            >
              Next
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
