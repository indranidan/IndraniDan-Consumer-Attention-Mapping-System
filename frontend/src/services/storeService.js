/**
 * Store Management Service
 * ========================
 * API calls for stores, zones, shelves, products, cameras, and dashboard stats.
 * All functions return Axios promises.
 */

import api from "./api";
import { runScoringAnalysis, invalidateScoringCache } from "./scoringService";

// ── Global Client-Side SWR Cache Manager (with sessionStorage) ──
const _clientEntityCache = new Map();
const ENTITY_CACHE_TTL_MS = 60 * 1000; // 60 seconds
const SESSION_STORAGE_KEY_PREFIX = "app_cache_v1:";

// Populate initial in-memory cache from sessionStorage on startup
try {
  if (typeof window !== "undefined" && window.sessionStorage) {
    for (let i = 0; i < window.sessionStorage.length; i++) {
      const k = window.sessionStorage.key(i);
      if (k && k.startsWith(SESSION_STORAGE_KEY_PREFIX)) {
        const raw = window.sessionStorage.getItem(k);
        if (raw) {
          const parsed = JSON.parse(raw);
          const fullKey = k.slice(SESSION_STORAGE_KEY_PREFIX.length);
          if (Date.now() - parsed.timestamp < (parsed.ttlMs || ENTITY_CACHE_TTL_MS)) {
            _clientEntityCache.set(fullKey, parsed);
          } else {
            window.sessionStorage.removeItem(k);
          }
        }
      }
    }
  }
} catch (e) {
  // Silent fallback if sessionStorage is disabled or restricted
}

export const invalidateClientCache = (...tags) => {
  if (!tags || tags.length === 0) {
    _clientEntityCache.clear();
    try {
      if (typeof window !== "undefined" && window.sessionStorage) {
        const keysToRemove = [];
        for (let i = 0; i < window.sessionStorage.length; i++) {
          const k = window.sessionStorage.key(i);
          if (k && k.startsWith(SESSION_STORAGE_KEY_PREFIX)) {
            keysToRemove.push(k);
          }
        }
        keysToRemove.forEach((k) => window.sessionStorage.removeItem(k));
      }
    } catch (_) {}
    return;
  }

  for (const tag of tags) {
    for (const key of Array.from(_clientEntityCache.keys())) {
      if (key.startsWith(`${tag}:`)) {
        _clientEntityCache.delete(key);
        try {
          if (typeof window !== "undefined" && window.sessionStorage) {
            window.sessionStorage.removeItem(`${SESSION_STORAGE_KEY_PREFIX}${key}`);
          }
        } catch (_) {}
      }
    }
  }
};

export const getSyncCachedData = (tag, key = "default") => {
  const fullKey = `${tag}:${key}`;
  const now = Date.now();
  if (_clientEntityCache.has(fullKey)) {
    const cached = _clientEntityCache.get(fullKey);
    if (now - cached.timestamp < (cached.ttlMs || ENTITY_CACHE_TTL_MS)) {
      return cached.data;
    }
    _clientEntityCache.delete(fullKey);
  }
  return null;
};

export const hasSyncCachedData = (tag, key = "default") => {
  return getSyncCachedData(tag, key) !== null;
};

const cachedGet = async (tag, key, fetcher, ttlMs = ENTITY_CACHE_TTL_MS, forceFresh = false) => {
  const fullKey = `${tag}:${key}`;
  const now = Date.now();
  if (!forceFresh && _clientEntityCache.has(fullKey)) {
    const cached = _clientEntityCache.get(fullKey);
    if (now - cached.timestamp < ttlMs) {
      return cached.data;
    }
    _clientEntityCache.delete(fullKey);
  }

  const res = await fetcher();
  const entry = {
    timestamp: now,
    ttlMs,
    data: {
      data: res.data,
      status: res.status,
      headers: res.headers || {},
    },
  };

  _clientEntityCache.set(fullKey, entry);
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.setItem(`${SESSION_STORAGE_KEY_PREFIX}${fullKey}`, JSON.stringify(entry));
    }
  } catch (_) {}

  return res;
};


// ── Dashboard ────────────────────────────────────────────────
export const getDashboardStats = (forceFresh = false) =>
  cachedGet("dashboard", "stats", () => api.get("/api/dashboard/stats"), 30000, forceFresh);

// ── Stores ───────────────────────────────────────────────────
export const getStores = (params = {}, forceFresh = false) =>
  cachedGet("stores", JSON.stringify(params), () => api.get("/api/stores", { params }), ENTITY_CACHE_TTL_MS, forceFresh);

export const getStoreById = (id, forceFresh = false) =>
  cachedGet("stores", `id:${id}`, () => api.get(`/api/stores/${id}`), ENTITY_CACHE_TTL_MS, forceFresh);

export const createStore = async (data) => {
  const res = await api.post("/api/stores", data);
  invalidateClientCache("stores", "dashboard");
  return res;
};

export const updateStore = async (id, data) => {
  const res = await api.put(`/api/stores/${id}`, data);
  invalidateClientCache("stores", "dashboard");
  return res;
};

export const deleteStore = async (id) => {
  const res = await api.delete(`/api/stores/${id}`);
  invalidateClientCache("stores", "zones", "shelves", "products", "cameras", "dashboard");
  return res;
};

// ── Zones ────────────────────────────────────────────────────
export const getZones = (params = {}, forceFresh = false) =>
  cachedGet("zones", JSON.stringify(params), () => api.get("/api/zones", { params }), ENTITY_CACHE_TTL_MS, forceFresh);

export const getZoneById = (id, forceFresh = false) =>
  cachedGet("zones", `id:${id}`, () => api.get(`/api/zones/${id}`), ENTITY_CACHE_TTL_MS, forceFresh);

export const createZone = async (data) => {
  const res = await api.post("/api/zones", data);
  invalidateClientCache("zones", "dashboard");
  return res;
};

export const updateZone = async (id, data) => {
  const res = await api.put(`/api/zones/${id}`, data);
  invalidateClientCache("zones", "dashboard");
  return res;
};

export const deleteZone = async (id) => {
  const res = await api.delete(`/api/zones/${id}`);
  invalidateClientCache("zones", "shelves", "products", "dashboard");
  return res;
};

// ── Shelves ──────────────────────────────────────────────────
export const getShelves = (params = {}, forceFresh = false) =>
  cachedGet("shelves", JSON.stringify(params), () => api.get("/api/shelves", { params }), ENTITY_CACHE_TTL_MS, forceFresh);

export const getShelfById = (id, forceFresh = false) =>
  cachedGet("shelves", `id:${id}`, () => api.get(`/api/shelves/${id}`), ENTITY_CACHE_TTL_MS, forceFresh);

export const createShelf = async (data) => {
  const res = await api.post("/api/shelves", data);
  invalidateClientCache("shelves", "dashboard");
  return res;
};

export const updateShelf = async (id, data) => {
  const res = await api.put(`/api/shelves/${id}`, data);
  invalidateClientCache("shelves", "dashboard");
  return res;
};

export const deleteShelf = async (id) => {
  const res = await api.delete(`/api/shelves/${id}`);
  invalidateClientCache("shelves", "products", "dashboard");
  return res;
};

// ── Products ─────────────────────────────────────────────────
export const getProducts = (params = {}, forceFresh = false) =>
  cachedGet("products", JSON.stringify(params), () => api.get("/api/products", { params }), ENTITY_CACHE_TTL_MS, forceFresh);

export const getProductById = (id, forceFresh = false) =>
  cachedGet("products", `id:${id}`, () => api.get(`/api/products/${id}`), ENTITY_CACHE_TTL_MS, forceFresh);

export const createProduct = async (data) => {
  const res = await api.post("/api/products", data);
  invalidateClientCache("products", "dashboard");
  return res;
};

export const updateProduct = async (id, data) => {
  const res = await api.put(`/api/products/${id}`, data);
  invalidateClientCache("products", "dashboard");
  return res;
};

export const deleteProduct = async (id) => {
  const res = await api.delete(`/api/products/${id}`);
  invalidateClientCache("products", "dashboard");
  return res;
};

// ── Cameras ──────────────────────────────────────────────────
export const getCameras = (params = {}, forceFresh = false) =>
  cachedGet("cameras", JSON.stringify(params), () => api.get("/api/cameras", { params }), ENTITY_CACHE_TTL_MS, forceFresh);

export const getCameraById = (id, forceFresh = false) =>
  cachedGet("cameras", `id:${id}`, () => api.get(`/api/cameras/${id}`), ENTITY_CACHE_TTL_MS, forceFresh);

export const createCamera = async (data) => {
  const res = await api.post("/api/cameras", data);
  invalidateClientCache("cameras", "dashboard");
  return res;
};

export const updateCamera = async (id, data) => {
  const res = await api.put(`/api/cameras/${id}`, data);
  invalidateClientCache("cameras", "dashboard");
  return res;
};

export const deleteCamera = async (id) => {
  const res = await api.delete(`/api/cameras/${id}`);
  invalidateClientCache("cameras", "dashboard");
  return res;
};


// ── AI Analytics ─────────────────────────────────────────────
export const createAIJob = (data) => {
  if (data instanceof FormData) {
    return api.post("/api/ai/jobs", data, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }
  const formData = new FormData();
  Object.keys(data).forEach((key) => {
    if (data[key] !== undefined && data[key] !== null) {
      const val =
        typeof data[key] === "object" && !(data[key] instanceof File)
          ? JSON.stringify(data[key])
          : data[key];
      formData.append(key, val);
    }
  });
  return api.post("/api/ai/jobs", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getAIJobs = (params = {}) =>
  api.get("/api/ai/jobs", { params });

export const getAIJob = (jobId) => api.get(`/api/ai/jobs/${jobId}`);

export const stopAIJob = (jobId) => api.post(`/api/ai/jobs/${jobId}/stop`);

export const getAIJobResults = (jobId) =>
  api.get(`/api/ai/jobs/${jobId}/results`);

export const getAIJobReport = (jobId) =>
  api.get(`/api/ai/jobs/${jobId}/report`);

export const getAIFileUrl = (jobId, filePath) => {
  const token = localStorage.getItem("access_token");
  const base = `${api.defaults.baseURL}/api/ai/results/${jobId}/files/${filePath}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
};


// ── Attention Analysis Engine ───────────────────────────────────
export const getAttentionAnalysis = (jobId) =>
  api.get(`/api/v1/attention/jobs/${jobId}/attention-analysis`);

export const getAttentionShelfMetrics = (jobId) =>
  api.get(`/api/v1/attention/jobs/${jobId}/shelf-metrics`);

export const getAttentionProductMetrics = (jobId) =>
  api.get(`/api/v1/attention/jobs/${jobId}/product-metrics`);

export const getAttentionEvents = (jobId, params = {}) =>
  api.get(`/api/v1/attention/jobs/${jobId}/events`, { params });

export const getAttentionReport = (jobId) =>
  api.get(`/api/v1/attention/jobs/${jobId}/report`);

export const getAttentionHeatmap = (jobId) =>
  api.get(`/api/v1/attention/jobs/${jobId}/heatmap`);

export const runAttentionJob = (jobId) =>
  api.post(`/api/v1/attention/jobs/${jobId}/run`);

// Backward-compatible aliases
export const getModule4Analysis = getAttentionAnalysis;
export const getModule4ShelfMetrics = getAttentionShelfMetrics;
export const getModule4ProductMetrics = getAttentionProductMetrics;
export const getModule4Events = getAttentionEvents;
export const getModule4Report = getAttentionReport;
export const getModule4Heatmap = getAttentionHeatmap;
export const runModule4Job = runAttentionJob;


// ── Product Interaction Analysis ───────────────────────────────
export const getInteractionAnalysis = (jobId) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/interaction-analysis`);

export const getProductEngagement = (jobId) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/product-engagement`);

export const getShelfInteractions = (jobId) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/shelf-interactions`);

export const getInteractionEvents = (jobId, params = {}) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/events`, { params });

export const getProductComparisons = (jobId) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/comparisons`);

export const getInteractionReport = (jobId) =>
  api.get(`/api/v1/interactions/jobs/${jobId}/report`);

export const runInteractionJob = (jobId) =>
  api.post(`/api/v1/interactions/jobs/${jobId}/run`);

// Backward-compatible aliases
export const getModule5Analysis = getInteractionAnalysis;
export const getModule5ProductEngagement = getProductEngagement;
export const getModule5ShelfInteractions = getShelfInteractions;
export const getModule5Events = getInteractionEvents;
export const getModule5Comparisons = getProductComparisons;
export const getModule5Report = getInteractionReport;
export const runModule5Job = runInteractionJob;


// ── MongoDB Shopper Trajectories & WebSocket Stream ──────────
export const getShopperTrajectories = (jobId, params = {}) =>
  api.get(`/api/ai/jobs/${jobId}/trajectories`, { params });

export const getShopperTrajectory = (jobId, trackingId) =>
  api.get(`/api/ai/jobs/${jobId}/trajectories/${trackingId}`);

export const createJobWebSocket = (jobId, onMessage, onError, onClose) => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
  const wsUrl = `${protocol}//${host}/api/ai/jobs/${jobId}/ws`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (err) {
      console.warn("WebSocket parse error:", err);
    }
  };

  if (onError) ws.onerror = onError;
  if (onClose) ws.onclose = onClose;

  return ws;
};

// ── Unified AI Job Orchestration ─────────────────────────────
export const reEvaluateAIJob = async (jobId) => {
  const [attentionRes, interactionRes, behaviorRes, scoringRes] = await Promise.all([
    runAttentionJob(jobId),
    runInteractionJob(jobId),
    runBehaviorJob(jobId),
    runScoringAnalysis(jobId).catch((err) => {
      console.warn("Module 8 scoring rerun skipped/failed:", err);
      return { data: null };
    }),
  ]);
  return {
    attention: attentionRes.data,
    interaction: interactionRes.data,
    behavior: behaviorRes.data,
    scoring: scoringRes?.data || scoringRes,
  };
};

// ── In-Memory Session Cache for Unified AI Datasets & Behavior Intelligence ──
const _unifiedDataCache = new Map();
const _behaviorCache = new Map();
const UNIFIED_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

export const invalidateUnifiedDataCache = (jobId = null) => {
  if (jobId) {
    _unifiedDataCache.delete(jobId);
    _behaviorCache.delete(jobId);
    invalidateScoringCache(`scores:${jobId}`);
    invalidateScoringCache(`leaderboard:${jobId}`);
  } else {
    _unifiedDataCache.clear();
    _behaviorCache.clear();
    invalidateScoringCache();
  }
};

export const getUnifiedAIJobData = async (jobId, forceFresh = false) => {
  const now = Date.now();
  if (!forceFresh && _unifiedDataCache.has(jobId)) {
    const cached = _unifiedDataCache.get(jobId);
    if (now - cached.timestamp < UNIFIED_CACHE_TTL_MS) {
      return cached.data;
    }
    _unifiedDataCache.delete(jobId);
  }

  const [
    resultsRes,
    reportRes,
    attentionRes,
    interactionRes,
    heatmapRes,
    behaviorRes,
  ] = await Promise.allSettled([
    getAIJobResults(jobId),
    getAIJobReport(jobId),
    getAttentionAnalysis(jobId),
    getInteractionAnalysis(jobId),
    getAttentionHeatmap(jobId),
    getBehaviorAnalysis(jobId, forceFresh),
  ]);

  const data = {
    results: resultsRes.status === "fulfilled" ? resultsRes.value.data : null,
    report: reportRes.status === "fulfilled" ? reportRes.value.data : null,
    attention: attentionRes.status === "fulfilled" ? attentionRes.value.data : null,
    interaction: interactionRes.status === "fulfilled" ? interactionRes.value.data : null,
    heatmap: heatmapRes.status === "fulfilled" ? heatmapRes.value.data : null,
    behavior: behaviorRes.status === "fulfilled" ? behaviorRes.value.data : null,
  };

  _unifiedDataCache.set(jobId, { timestamp: now, data });
  return data;
};

export const getDashboardAnalytics = (storeId = null, forceFresh = false) => {
  const url = storeId ? `/api/dashboard/analytics?store_id=${storeId}` : `/api/dashboard/analytics`;
  return cachedGet("dashboard", `analytics_${storeId || "global"}`, () => api.get(url), 20000, forceFresh);
};
export const testCameraStream = (cameraId) => api.post(`/api/cameras/${cameraId}/test`);
export const getCameraSnapshot = (cameraId) => api.get(`/api/cameras/${cameraId}/snapshot`);


// ── Module 6: Consumer Behavior Intelligence ───────────────────
export const runBehaviorJob = async (jobId) => {
  invalidateUnifiedDataCache(jobId);
  return api.post(`/api/behavior/${jobId}/analyze?force_recompute=true`);
};

export const getBehaviorAnalysis = async (jobId, forceFresh = false) => {
  const now = Date.now();
  if (!forceFresh && _behaviorCache.has(jobId)) {
    const cached = _behaviorCache.get(jobId);
    if (now - cached.timestamp < UNIFIED_CACHE_TTL_MS) {
      return cached.data;
    }
    _behaviorCache.delete(jobId);
  }
  const res = await api.get(`/api/behavior/${jobId}/analysis`);
  _behaviorCache.set(jobId, { timestamp: now, data: res });
  return res;
};

export const getBehaviorJourneys = (jobId) =>
  api.get(`/api/behavior/${jobId}/journeys`);

export const getBehaviorTransitions = (jobId) =>
  api.get(`/api/behavior/${jobId}/transitions`);

export const getBehaviorFunnel = (jobId) =>
  api.get(`/api/behavior/${jobId}/funnel`);

export const runModule6Job = runBehaviorJob;
export const getModule6Analysis = getBehaviorAnalysis;
export const getModule6Journeys = getBehaviorJourneys;
export const getModule6Transitions = getBehaviorTransitions;
export const getModule6Funnel = getBehaviorFunnel;



