/**
 * Store Management Service
 * ========================
 * API calls for stores, zones, shelves, products, cameras, and dashboard stats.
 * All functions return Axios promises.
 */

import api from "./api";

// ── Dashboard ────────────────────────────────────────────────
export const getDashboardStats = () => api.get("/api/dashboard/stats");

// ── Stores ───────────────────────────────────────────────────
export const getStores = (params = {}) =>
  api.get("/api/stores", { params });

export const getStoreById = (id) => api.get(`/api/stores/${id}`);

export const createStore = (data) => api.post("/api/stores", data);

export const updateStore = (id, data) => api.put(`/api/stores/${id}`, data);

export const deleteStore = (id) => api.delete(`/api/stores/${id}`);

// ── Zones ────────────────────────────────────────────────────
export const getZones = (params = {}) =>
  api.get("/api/zones", { params });

export const getZoneById = (id) => api.get(`/api/zones/${id}`);

export const createZone = (data) => api.post("/api/zones", data);

export const updateZone = (id, data) => api.put(`/api/zones/${id}`, data);

export const deleteZone = (id) => api.delete(`/api/zones/${id}`);

// ── Shelves ──────────────────────────────────────────────────
export const getShelves = (params = {}) =>
  api.get("/api/shelves", { params });

export const getShelfById = (id) => api.get(`/api/shelves/${id}`);

export const createShelf = (data) => api.post("/api/shelves", data);

export const updateShelf = (id, data) => api.put(`/api/shelves/${id}`, data);

export const deleteShelf = (id) => api.delete(`/api/shelves/${id}`);

// ── Products ─────────────────────────────────────────────────
export const getProducts = (params = {}) =>
  api.get("/api/products", { params });

export const getProductById = (id) => api.get(`/api/products/${id}`);

export const createProduct = (data) => api.post("/api/products", data);

export const updateProduct = (id, data) => api.put(`/api/products/${id}`, data);

export const deleteProduct = (id) => api.delete(`/api/products/${id}`);

// ── Cameras ──────────────────────────────────────────────────
export const getCameras = (params = {}) =>
  api.get("/api/cameras", { params });

export const getCameraById = (id) => api.get(`/api/cameras/${id}`);

export const createCamera = (data) => api.post("/api/cameras", data);

export const updateCamera = (id, data) => api.put(`/api/cameras/${id}`, data);

export const deleteCamera = (id) => api.delete(`/api/cameras/${id}`);
