/**
 * Alert Service
 * ==============
 * REST API calls and WebSocket connection factory for the Module 11
 * Notification & Alert System.
 */

import api from "./api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "";

// ── REST API Helpers ─────────────────────────────────────────

/**
 * Fetch paginated notifications for the current user's role.
 */
export const getAlerts = async ({
  storeId,
  severity,
  type,
  isRead,
  skip = 0,
  limit = 20,
} = {}) => {
  const params = { skip, limit };
  if (storeId) params.store_id = storeId;
  if (severity) params.severity = severity;
  if (type) params.type = type;
  if (isRead !== undefined && isRead !== null) params.is_read = isRead;

  const { data } = await api.get("/api/alerts/", { params });
  return data;
};

/**
 * Get the unread notification count for the navbar badge.
 */
export const getUnreadCount = async (storeId) => {
  const params = {};
  if (storeId) params.store_id = storeId;
  const { data } = await api.get("/api/alerts/unread-count", { params });
  return data.unread_count;
};

/**
 * Mark a single notification as read.
 */
export const markAlertRead = async (notificationId) => {
  const { data } = await api.post(`/api/alerts/${notificationId}/read`);
  return data;
};

/**
 * Mark all notifications as read for the current user.
 */
export const markAllAlertsRead = async (storeId) => {
  const params = {};
  if (storeId) params.store_id = storeId;
  const { data } = await api.post("/api/alerts/read-all", null, { params });
  return data;
};

/**
 * Resolve a specific alert.
 */
export const resolveAlert = async (notificationId) => {
  const { data } = await api.post(`/api/alerts/${notificationId}/resolve`);
  return data;
};

/**
 * Delete a specific alert.
 */
export const deleteAlert = async (notificationId) => {
  const { data } = await api.delete(`/api/alerts/${notificationId}`);
  return data;
};

/**
 * Manually trigger alert evaluation (diagnostic / admin tool).
 */
export const triggerEvaluation = async () => {
  const { data } = await api.post("/api/alerts/evaluate");
  return data;
};

// ── WebSocket Connection Factory ─────────────────────────────

/**
 * Create an authenticated WebSocket connection for real-time alert streaming.
 *
 * @param {Object}   options
 * @param {Function} options.onAlert   - Called with alert payload on each incoming alert
 * @param {Function} options.onOpen    - Called when connection opens
 * @param {Function} options.onClose   - Called when connection closes
 * @param {Function} options.onError   - Called on connection error
 * @returns {{ ws: WebSocket, close: Function }}
 */
export const createAlertWebSocket = ({
  onAlert,
  onOpen,
  onClose,
  onError,
} = {}) => {
  const token = localStorage.getItem("access_token");
  if (!token) {
    console.warn("[AlertService] No access token found, skipping WebSocket");
    return null;
  }

  // Vercel does not support WebSockets. We must connect directly to the Render backend.
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const defaultWsHost = window.location.hostname === "localhost" ? "localhost:8000" : "cams-backend-gan7.onrender.com";
  const wsHost = import.meta.env.VITE_WS_HOST || defaultWsHost;
  const wsUrl = `${wsProtocol}//${wsHost}/api/alerts/ws?token=${encodeURIComponent(token)}`;

  let isManualClose = false;
  let pingInterval = null;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[AlertService] WebSocket connected");
    onOpen?.();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "ALERT_CREATED" && data.alert) {
        onAlert?.(data.alert);
      }
    } catch (err) {
      console.warn("[AlertService] Failed to parse WS message:", err);
    }
  };

  ws.onclose = (event) => {
    if (pingInterval) clearInterval(pingInterval);
    console.log("[AlertService] WebSocket closed:", event.code);
    if (!isManualClose) {
      onClose?.(event);
    }
  };

  ws.onerror = (error) => {
    console.error("[AlertService] WebSocket error:", error);
    onError?.(error);
  };

  // Keep-alive ping every 30s
  pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send("ping");
    }
  }, 30000);

  const close = () => {
    isManualClose = true;
    if (pingInterval) clearInterval(pingInterval);
    try {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, "Client closed connection");
      }
    } catch (err) {
      // ignore
    }
  };

  return { ws, close };
};

export default {
  getAlerts,
  getUnreadCount,
  markAlertRead,
  markAllAlertsRead,
  resolveAlert,
  deleteAlert,
  triggerEvaluation,
  createAlertWebSocket,
};
