/**
 * Active Alerts Card
 * ===================
 * Dashboard widget displaying role-tailored top 3 unread alerts
 * with quick-resolve action and severity indicators.
 */

import { useNavigate } from "react-router-dom";
import { useNotifications } from "../../context/NotificationContext";

// Severity color mapping
const SEVERITY_CONFIG = {
  critical: {
    gradient: "from-red-500/20 to-red-600/10",
    border: "border-red-500/30",
    dot: "bg-red-500",
    text: "text-red-400",
    badge: "bg-red-500/15 text-red-400 border-red-500/30",
  },
  warning: {
    gradient: "from-amber-500/20 to-amber-600/10",
    border: "border-amber-500/30",
    dot: "bg-amber-500",
    text: "text-amber-400",
    badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
  info: {
    gradient: "from-blue-500/20 to-blue-600/10",
    border: "border-blue-500/30",
    dot: "bg-blue-500",
    text: "text-blue-400",
    badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
};

const ENTITY_ROUTES = {
  camera: "/cameras",
  shelf: "/shelves",
  product: "/products",
  zone: "/zones",
  ai_job: "/analytics",
  system: "/dashboard",
};

export default function ActiveAlertsCard() {
  const navigate = useNavigate();
  const { notifications, unreadCount, resolve, markRead } = useNotifications();

  // Filter to top 3 unread, unresolved alerts
  const activeAlerts = notifications
    .filter((n) => !n.is_read && !n.is_resolved)
    .slice(0, 3);

  const handleAlertClick = (alert) => {
    markRead(alert.id);
    const route = ENTITY_ROUTES[alert.entity_type || alert.alert_type];
    if (route) navigate(route);
  };

  const handleResolve = (e, alertId) => {
    e.stopPropagation();
    resolve(alertId);
  };

  return (
    <div className="bg-gray-900/60 backdrop-blur-xl rounded-2xl border border-gray-800/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800/40">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500/20 to-amber-500/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Active Alerts</h3>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">Real-time monitoring</p>
          </div>
        </div>
        {unreadCount > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 text-[10px] font-bold border border-red-500/30">
            {unreadCount} unread
          </span>
        )}
      </div>

      {/* Alerts List */}
      <div className="p-3 space-y-2">
        {activeAlerts.length === 0 ? (
          <div className="text-center py-6">
            <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-2">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-400 font-medium">All Clear</p>
            <p className="text-xs text-gray-600 mt-0.5">No active alerts at this time</p>
          </div>
        ) : (
          activeAlerts.map((alert) => {
            const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
            return (
              <div
                key={alert.id}
                onClick={() => handleAlertClick(alert)}
                className={`group relative flex items-start gap-3 px-3 py-2.5 rounded-xl cursor-pointer
                  bg-gradient-to-r ${config.gradient} border ${config.border}
                  hover:scale-[1.01] transition-all duration-200`}
              >
                {/* Severity dot */}
                <span className={`flex-shrink-0 w-2 h-2 rounded-full ${config.dot} mt-1.5 animate-pulse`} />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-white truncate">{alert.title}</p>
                    <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${config.badge}`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{alert.message}</p>
                </div>

                {/* Quick resolve */}
                <button
                  onClick={(e) => handleResolve(e, alert.id)}
                  className="flex-shrink-0 opacity-0 group-hover:opacity-100 px-2 py-1 rounded-lg
                    bg-emerald-500/15 text-emerald-400 text-[10px] font-bold border border-emerald-500/30
                    hover:bg-emerald-500/25 transition-all duration-200"
                >
                  Resolve
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
