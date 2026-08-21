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
      formData.append(key, data[key]);
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


// ── Module 4: Attention Analysis Engine ───────────────────────
export const getModule4Analysis = (jobId) =>
  api.get(`/api/module4/jobs/${jobId}/attention-analysis`);

export const getModule4ShelfMetrics = (jobId) =>
  api.get(`/api/module4/jobs/${jobId}/shelf-metrics`);

export const getModule4ProductMetrics = (jobId) =>
  api.get(`/api/module4/jobs/${jobId}/product-metrics`);

export const getModule4Events = (jobId, params = {}) =>
  api.get(`/api/module4/jobs/${jobId}/events`, { params });

export const getModule4Report = (jobId) =>
  api.get(`/api/module4/jobs/${jobId}/report`);

export const getModule4Heatmap = (jobId) =>
  api.get(`/api/module4/jobs/${jobId}/heatmap`);

export const runModule4Job = (jobId) =>
  api.post(`/api/module4/jobs/${jobId}/run`);


// ── Module 5: Product Interaction Analysis ────────────────────
export const getModule5Analysis = (jobId) =>
  api.get(`/api/module5/jobs/${jobId}/interaction-analysis`);

export const getModule5ProductEngagement = (jobId) =>
  api.get(`/api/module5/jobs/${jobId}/product-engagement`);

export const getModule5ShelfInteractions = (jobId) =>
  api.get(`/api/module5/jobs/${jobId}/shelf-interactions`);

export const getModule5Events = (jobId, params = {}) =>
  api.get(`/api/module5/jobs/${jobId}/events`, { params });

export const getModule5Comparisons = (jobId) =>
  api.get(`/api/module5/jobs/${jobId}/comparisons`);

export const getModule5Report = (jobId) =>
  api.get(`/api/module5/jobs/${jobId}/report`);

export const runModule5Job = (jobId) =>
  api.post(`/api/module5/jobs/${jobId}/run`);



