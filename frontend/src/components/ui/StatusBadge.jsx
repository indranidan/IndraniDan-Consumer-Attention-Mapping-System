/**
 * StatusBadge Component
 * ======================
 * Displays a colored status indicator badge.
 */

const statusStyles = {
  active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  inactive: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  maintenance: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export default function StatusBadge({ status }) {
  const style = statusStyles[status?.toLowerCase()] || statusStyles.inactive;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-xs font-medium border ${style}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          status?.toLowerCase() === "active"
            ? "bg-emerald-400"
            : status?.toLowerCase() === "maintenance"
            ? "bg-amber-400"
            : "bg-gray-400"
        }`}
      />
      {status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown"}
    </span>
  );
}
