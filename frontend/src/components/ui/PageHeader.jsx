/**
 * PageHeader Component
 * =====================
 * Reusable page header with title, description, and optional action button.
 */

export default function PageHeader({
  title,
  description,
  actionLabel,
  onAction,
  showAction = true,
  icon,
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          {icon && (
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-violet-500/20">
              {icon}
            </div>
          )}
          {title}
        </h1>
        {description && (
          <p className="text-sm text-gray-500 mt-1 ml-[52px]">{description}</p>
        )}
      </div>

      {showAction && actionLabel && (
        <button
          onClick={onAction}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 transition-all duration-300"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
