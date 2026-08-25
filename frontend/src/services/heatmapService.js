/**
 * Heatmap Service
 * ================
 * API client helpers for Module 7 heatmap endpoints.
 * Fetches spatial density matrices, shelf vertical tier analytics,
 * traffic flow data, and hotspot diagnostics.
 */

import api from "./api";

// ── In-Memory Session Cache ──────────────────────────────────
const _heatmapCache = new Map();
const HEATMAP_CACHE_TTL_MS = 30 * 1000; // 30 seconds

function _getCached(key) {
  const entry = _heatmapCache.get(key);
  if (entry && Date.now() - entry.ts < HEATMAP_CACHE_TTL_MS) {
    return entry.data;
  }
  if (entry) _heatmapCache.delete(key);
  return null;
}

function _setCache(key, data) {
  _heatmapCache.set(key, { data, ts: Date.now() });
}

export function invalidateHeatmapCache(prefix) {
  if (!prefix) {
    _heatmapCache.clear();
    return;
  }
  for (const key of _heatmapCache.keys()) {
    if (key.startsWith(prefix)) _heatmapCache.delete(key);
  }
}

// ── Store-Wide Heatmap ───────────────────────────────────────

export async function getStoreHeatmap(storeId, { colormap = "JET", sigma = 8.0 } = {}) {
  const cacheKey = `store:${storeId}:${colormap}:${sigma}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/heatmaps/store/${storeId}`, {
    params: { colormap, sigma },
  });
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Shelf-Level Heatmap ──────────────────────────────────────

export async function getShelfHeatmap(shelfId) {
  const cacheKey = `shelf:${shelfId}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/heatmaps/shelf/${shelfId}`);
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Traffic Flow ─────────────────────────────────────────────

export async function getTrafficHeatmap(storeId) {
  const cacheKey = `traffic:${storeId}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/heatmaps/traffic/${storeId}`);
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Job-Level Heatmap ────────────────────────────────────────

export async function getJobHeatmap(jobId, { colormap = "JET", sigma = 8.0 } = {}) {
  const cacheKey = `job:${jobId}:${colormap}:${sigma}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/heatmaps/job/${jobId}`, {
    params: { colormap, sigma },
  });
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Job Heatmap Image URL ────────────────────────────────────

export function getJobHeatmapImageUrl(jobId, colormap = "JET") {
  return `${api.defaults.baseURL}/api/heatmaps/job/${jobId}/image?colormap=${colormap}`;
}
