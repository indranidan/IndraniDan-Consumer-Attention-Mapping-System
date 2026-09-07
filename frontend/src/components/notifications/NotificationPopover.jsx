/**
 * Notification Popover
 * =====================
 * Glassmorphic dropdown notification panel anchored beneath the bell icon
 * in the top navbar. Features:
 * - Pulsing unread badge
 * - Severity color indicators
 * - "Mark all read" button
 * - Deep-linking to /cameras, /shelves, /analytics, /zones
 * - Clickable notification items
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useNotifications } from "../../context/NotificationContext";

// ── Deep-link mapping ────────────────────────────────────────
const ENTITY_DEEP_LINKS = {
  camera: "/cameras",
  shelf: "/shelves",
  product: "/products",
  zone: "/zones",
  ai_job: "/analytics",
  system: "/dashboard",
};

// ── Severity styling ─────────────────────────────────────────
const SEVERITY_STYLES = {
  critical: {
    dot: "bg-red-500",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    label: "Critical",
  },
  warning: {
    dot: "bg-amber-500",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    label: "Warning",
  },
  info: {
    dot: "bg-blue-500",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    text: "text-blue-400",
    label: "Info",
  },
};

// ── Alert type icons ─────────────────────────────────────────
const TYPE_ICONS = {
  camera_health: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  shelf_performance: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
    </svg>
  ),
  product_visibility: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  traffic_anomaly: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  ),
  platform: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

function timeAgo(dateStr) {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
}

export default function NotificationPopover() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef(null);
  const {
    unreadCount,
    notifications,
    markRead,
    markAllRead,
    resolve,
    refreshNotifications,
  } = useNotifications();

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Refresh on open
  useEffect(() => {
    if (isOpen) {
      refreshNotifications({ limit: 15 });
    }
  }, [isOpen, refreshNotifications]);

  const handleNotificationClick = (notif) => {
    // Mark as read
    if (!notif.is_read) {
      markRead(notif.id);
    }

    // Deep-link navigation
    const entityType = notif.entity_type || notif.alert_type;
    const deepLink = ENTITY_DEEP_LINKS[entityType];
    if (deepLink) {
      navigate(deepLink);
    }

    setIsOpen(false);
  };

  const handleResolve = (e, notifId) => {
    e.stopPropagation();
    resolve(notifId);
  };

  return (
    <div className="relative" ref={popoverRef}>
      {/* ── Bell Button ───────────────────────────────────────── */}
      <button
        id="notification-bell"
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all duration-200"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold shadow-lg shadow-red-500/40 animate-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* ── Popover Panel ─────────────────────────────────────── */}
      {isOpen && (
        <div
          className="absolute right-0 top-full mt-2 w-96 max-h-[480px] rounded-2xl overflow-hidden z-50
          bg-gray-900/95 backdrop-blur-2xl border border-gray-700/50
          shadow-2xl shadow-black/50"
          style={{ animation: "fadeSlideIn 0.2s ease-out" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800/50">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">Notifications</h3>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-md bg-violet-500/20 text-violet-400 text-[10px] font-bold">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllRead()}
                className="text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="overflow-y-auto max-h-[400px] divide-y divide-gray-800/30">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4">
                <svg className="w-12 h-12 text-gray-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                <p className="text-sm text-gray-500">No notifications yet</p>
                <p className="text-xs text-gray-600 mt-1">Alerts will appear here as they're generated</p>
              </div>
            ) : (
              notifications.map((notif) => {
                const severity = SEVERITY_STYLES[notif.severity] || SEVERITY_STYLES.info;
                const alertType = notif.alert_type || notif.type;
                const icon = TYPE_ICONS[alertType] || TYPE_ICONS.platform;

                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-all duration-150
                      hover:bg-gray-800/40
                      ${!notif.is_read ? "bg-gray-800/20" : "opacity-70"}`}
                  >
                    {/* Icon */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${severity.bg} border ${severity.border} flex items-center justify-center ${severity.text} mt-0.5`}>
                      {icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`inline-block w-1.5 h-1.5 rounded-full ${severity.dot} ${!notif.is_read ? "animate-pulse" : ""}`} />
                        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                          {severity.label}
                        </span>
                        <span className="text-[10px] text-gray-600 ml-auto flex-shrink-0">
                          {timeAgo(notif.created_at)}
                        </span>
                      </div>
                      <p className={`text-sm font-medium truncate ${!notif.is_read ? "text-white" : "text-gray-400"}`}>
                        {notif.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                        {notif.message}
                      </p>

                      {/* Quick actions */}
                      {!notif.is_resolved && (
                        <button
                          onClick={(e) => handleResolve(e, notif.id)}
                          className="mt-1.5 text-[10px] font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
                        >
                          ✓ Resolve
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Animation keyframes */}
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
