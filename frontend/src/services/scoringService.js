/**
 * Scoring Service
 * ================
 * API client helpers for Module 8 Product Attractiveness Scoring endpoints.
 * Fetches score cards, 5-pillar vectors, leaderboards, and intelligence reports.
 */

import api from "./api";

// ── In-Memory Session Cache ──────────────────────────────────
const _scoringCache = new Map();
const SCORING_CACHE_TTL_MS = 60 * 1000; // 60 seconds

function _getCached(key) {
  const entry = _scoringCache.get(key);
  if (entry && Date.now() - entry.ts < SCORING_CACHE_TTL_MS) {
    return entry.data;
  }
  if (entry) _scoringCache.delete(key);
  return null;
}

function _setCache(key, data) {
  _scoringCache.set(key, { data, ts: Date.now() });
}

export function invalidateScoringCache(prefix) {
  if (!prefix) {
    _scoringCache.clear();
    return;
  }
  for (const key of _scoringCache.keys()) {
    if (key.startsWith(prefix)) _scoringCache.delete(key);
  }
}

// ── Full Scoring Analysis ────────────────────────────────────

export async function getScoringAnalysis(jobId) {
  const cacheKey = `scores:${jobId}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/v1/scoring/jobs/${jobId}/scores`);
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Leaderboard ──────────────────────────────────────────────

export async function getScoringLeaderboard(jobId, topN = 5) {
  const cacheKey = `leaderboard:${jobId}:${topN}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/v1/scoring/jobs/${jobId}/leaderboard`, {
    params: { top_n: topN },
  });
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}

// ── Run / Refresh Scoring ────────────────────────────────────

export async function runScoringAnalysis(jobId) {
  invalidateScoringCache(`scores:${jobId}`);
  invalidateScoringCache(`leaderboard:${jobId}`);
  const res = await api.post(`/api/v1/scoring/jobs/${jobId}/run`);
  return res.data;
}

// ── Report ───────────────────────────────────────────────────

export async function getScoringReport(jobId) {
  const cacheKey = `report:${jobId}`;
  const cached = _getCached(cacheKey);
  if (cached) return cached;

  const res = await api.get(`/api/v1/scoring/jobs/${jobId}/report`);
  const data = res.data;
  _setCache(cacheKey, data);
  return data;
}
