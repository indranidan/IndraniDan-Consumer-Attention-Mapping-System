/**
 * Notification Context & Provider
 * ================================
 * Connects to the backend's alert WebSocket stream, maintains real-time
 * unread counts, and dispatches incoming alerts as toast notifications.
 *
 * Wraps the authenticated portion of the app — must sit inside AuthProvider
 * and ToastProvider.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { useToast } from "./ToastContext";
import { useAuth } from "../hooks/useAuth";
import {
  getUnreadCount,
  getAlerts,
  markAlertRead,
  markAllAlertsRead,
  resolveAlert,
  createAlertWebSocket,
} from "../services/alertService";

const NotificationContext = createContext(null);

// Map alert severity to toast type
const SEVERITY_TO_TOAST = {
  critical: "error",
  warning: "warning",
  info: "info",
};

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttempts = useRef(0);

  // ── Fetch initial data ─────────────────────────────────────

  const refreshUnreadCount = useCallback(async () => {
    try {
      const count = await getUnreadCount();
      setUnreadCount(count);
    } catch {
      // Silently fail — REST fallback
    }
  }, []);

  const refreshNotifications = useCallback(async (params = {}) => {
    setIsLoading(true);
    try {
      const data = await getAlerts(params);
      setNotifications(Array.isArray(data) ? data : (data?.data || []));
    } catch {
      // Silently fail
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Actions ────────────────────────────────────────────────

  const handleMarkRead = useCallback(
    async (notificationId) => {
      try {
        await markAlertRead(notificationId);
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId ? { ...n, is_read: true } : n
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // Silently fail
      }
    },
    []
  );

  const handleMarkAllRead = useCallback(async () => {
    try {
      await markAllAlertsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }, []);

  const handleResolve = useCallback(
    async (notificationId) => {
      try {
        await resolveAlert(notificationId);
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId
              ? { ...n, is_resolved: true, is_read: true }
              : n
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // Silently fail
      }
    },
    []
  );

  // ── WebSocket Connection ───────────────────────────────────

  const connectWebSocket = useCallback(() => {
    if (!user) return;

    // Prevent duplicate connections if already open or connecting
    if (
      wsRef.current?.ws &&
      (wsRef.current.ws.readyState === WebSocket.CONNECTING ||
        wsRef.current.ws.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    // Clean up existing dead connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const connection = createAlertWebSocket({
      onAlert: (alert) => {
        // Add to notifications list
        setNotifications((prev) => [alert, ...prev].slice(0, 50));
        setUnreadCount((prev) => prev + 1);

        // Show toast notification
        addToast({
          type: SEVERITY_TO_TOAST[alert.severity] || "info",
          title: alert.title,
          message: alert.message,
          duration: alert.severity === "critical" ? 8000 : 5000,
        });
      },
      onOpen: () => {
        reconnectAttempts.current = 0;
      },
      onClose: (event) => {
        // Do not auto-reconnect if client closed intentionally or user logged out
        if (event?.code === 1000 || !user) return;

        // Auto-reconnect with exponential backoff
        const delay = Math.min(
          1000 * 2 ** reconnectAttempts.current,
          30000
        );
        reconnectAttempts.current += 1;

        reconnectTimerRef.current = setTimeout(() => {
          connectWebSocket();
        }, delay);
      },
      onError: () => {
        // Error handler — reconnect handled by onClose
      },
    });

    if (connection) {
      wsRef.current = connection;
    }
  }, [user, addToast]);

  // ── Lifecycle ──────────────────────────────────────────────

  useEffect(() => {
    if (user?.email || user?.id) {
      refreshUnreadCount();
      refreshNotifications();
      connectWebSocket();
    } else {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [user?.email, user?.id, connectWebSocket, refreshUnreadCount, refreshNotifications]);

  // REST fallback: refresh unread count on route changes
  useEffect(() => {
    if (!user) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        refreshUnreadCount();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [user, refreshUnreadCount]);

  const value = {
    unreadCount,
    notifications,
    isLoading,
    refreshUnreadCount,
    refreshNotifications,
    markRead: handleMarkRead,
    markAllRead: handleMarkAllRead,
    resolve: handleResolve,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    return {
      unreadCount: 0,
      notifications: [],
      isLoading: false,
      refreshUnreadCount: () => {},
      refreshNotifications: () => {},
      markRead: () => {},
      markAllRead: () => {},
      resolve: () => {},
    };
  }
  return ctx;
}
