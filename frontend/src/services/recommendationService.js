/**
 * Recommendation Service
 * =======================
 * API client helpers for Module 9 Prescriptive Recommendations & Planogram Simulator.
 * Fetches categorized recommendations, summaries, and executes What-If simulations.
 */

import api from "./api";

// ── In-Memory Session Cache ──────────────────────────────────
const _recommendationCache = new Map();
const RECOMMENDATION_CACHE_TTL_MS = 60 * 1000; // 60 seconds

function _getCached(key) {
  const entry = _recommendationCache.get(key);
  if (entry && Date.now() - entry.ts < RECOMMENDATION_CACHE_TTL_MS) {
    return entry.data;
  }
  if (entry) _recommendationCache.delete(key);
  return null;
}

function _setCache(key, data) {
  _recommendationCache.set(key, { data, ts: Date.now() });
}

export function invalidateRecommendationCache(prefix) {
  if (!prefix) {
    _recommendationCache.clear();
    return;
  }
  for (const key of _recommendationCache.keys()) {
    if (key.startsWith(prefix)) _recommendationCache.delete(key);
  }
}

// ── Job-level Recommendations ────────────────────────────────

export async function getJobRecommendations(jobId, filters = {}) {
  const { category, priority } = filters;
  const cacheKey = `job-recs:${jobId}:${category || "all"}:${priority || "all"}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const params = {};
  if (category) params.category = category;
  if (priority) params.priority = priority;

  const res = await api.get(`/api/v1/recommendations/jobs/${jobId}`, { params });
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Store-level Recommendations ──────────────────────────────

export async function getStoreRecommendations(storeId, filters = {}) {
  const { category, priority } = filters;
  const cacheKey = `store-recs:${storeId}:${category || "all"}:${priority || "all"}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const params = { store_id: storeId };
  if (category) params.category = category;
  if (priority) params.priority = priority;

  const res = await api.get("/api/v1/recommendations", { params });
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Trigger / Refresh Recommendations ────────────────────────

export async function runJobRecommendations(jobId) {
  invalidateRecommendationCache(`job-recs:${jobId}`);
  const res = await api.post(`/api/v1/recommendations/jobs/${jobId}/run`);
  return res.data;
}

// ── What-If Planogram Simulation ─────────────────────────────

export async function simulatePlanogram(simulationPayload) {
  const res = await api.post("/api/v1/recommendations/simulate", simulationPayload);
  return res.data;
}
