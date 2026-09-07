/**
 * Reports & Export Service
 * ========================
 * Frontend API client for Module 12 Reports & Export System:
 * - Fetch available report templates
 * - Real-time zero-latency report preview
 * - Server-side dossier generation (PDF, Excel, CSV, JSON)
 * - Report history ledger & artifact download
 */

import api from "./api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const reportService = {
  /**
   * Fetch catalog of report templates
   */
  async getTemplates() {
    const response = await api.get("/api/reports/templates");
    return response.data;
  },

  /**
   * Preview aggregated analytics without file compilation
   */
  async previewReport(params) {
    const response = await api.post("/api/reports/preview", params);
    return response.data;
  },

  /**
   * Trigger official dossier generation
   */
  async generateReport(payload) {
    const response = await api.post("/api/reports/generate", payload);
    return response.data;
  },

  /**
   * List historical generated reports
   */
  async getLedger(params = {}) {
    const response = await api.get("/api/reports/ledger", { params });
    return response.data;
  },

  /**
   * Download a generated report file directly
   */
  async downloadReport(reportId, fallbackFilename = "report.pdf") {
    try {
      const response = await api.get(`/api/reports/${reportId}/download`, {
        responseType: "blob",
      });

      // Extract filename from header if available
      let filename = fallbackFilename;
      const disposition = response.headers["content-disposition"];
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      // Trigger browser download via blob URL
      const blob = new Blob([response.data], {
        type: response.headers["content-type"] || "application/octet-stream",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      return true;
    } catch (error) {
      console.error("Failed to download report:", error);
      throw error;
    }
  },

  /**
   * Delete report from disk and ledger
   */
  async deleteReport(reportId) {
    await api.delete(`/api/reports/${reportId}`);
    return true;
  },

  /**
   * Direct download link helper
   */
  getDownloadUrl(reportId) {
    return `${API_BASE_URL}/api/reports/${reportId}/download`;
  },
};

export default reportService;
