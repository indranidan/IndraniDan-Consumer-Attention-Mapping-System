import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  getUnifiedAIJobData,
  invalidateUnifiedDataCache,
  reEvaluateAIJob,
  getAttentionEvents,
  getInteractionEvents
} from '../services/storeService';
import api from '../services/api';
import { getJobHeatmap } from '../services/heatmapService';

const UnifiedJobContext = createContext();

export function UnifiedJobProvider({ children, job, isOpen, onClose }) {
  const jobId = job?.id;

  const [activeTab, setActiveTab] = useState("summary");
  
  const [unifiedData, setUnifiedData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reEvaluating, setReEvaluating] = useState(false);
  const [reEvalSuccess, setReEvalSuccess] = useState(false);

  const [heatmapViewMode, setHeatmapViewMode] = useState("attention");
  const [heatmapBlobUrl, setHeatmapBlobUrl] = useState(null);
  const [heatmapImgLoading, setHeatmapImgLoading] = useState(false);

  const [m7HeatmapData, setM7HeatmapData] = useState(null);
  const [m7HeatmapLoading, setM7HeatmapLoading] = useState(false);

  const [eventsList, setEventsList] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventSearch, setEventSearch] = useState("");
  const [eventFilterType, setEventFilterType] = useState("ALL");

  const [matrixSearch, setMatrixSearch] = useState("");
  const [matrixView, setMatrixView] = useState("shelves");

  const [reportViewMode, setReportViewMode] = useState("report");
  const [copied, setCopied] = useState(false);

  const loadAllData = useCallback(async (forceFresh = false) => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getUnifiedAIJobData(jobId, forceFresh);
      setUnifiedData(data);
    } catch (err) {
      console.error("Failed to load unified AI job data:", err);
      setError("Failed to load comprehensive AI job analytics.");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (isOpen && jobId) {
      loadAllData(false);
    }
  }, [isOpen, jobId, loadAllData]);

  const loadHeatmapImage = useCallback(async (imgUrlPath) => {
    if (!imgUrlPath) return;
    setHeatmapImgLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const fullUrl = imgUrlPath.startsWith("http")
        ? imgUrlPath
        : `${api.defaults.baseURL}${imgUrlPath}`;

      const res = await fetch(fullUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const blob = await res.blob();
        setHeatmapBlobUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return URL.createObjectURL(blob);
        });
      }
    } catch (err) {
      console.warn("Could not load heatmap blob:", err);
    } finally {
      setHeatmapImgLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "heatmap" && unifiedData?.heatmap?.image_url && !heatmapBlobUrl) {
      loadHeatmapImage(unifiedData.heatmap.image_url);
    }
  }, [activeTab, unifiedData, heatmapBlobUrl, loadHeatmapImage]);

  useEffect(() => {
    if (activeTab === "heatmaps" && jobId && !m7HeatmapData && !m7HeatmapLoading) {
      setM7HeatmapLoading(true);
      getJobHeatmap(jobId)
        .then((data) => {
          setM7HeatmapData(data);
          setM7HeatmapLoading(false);
        })
        .catch((err) => {
          console.warn("Module 7 heatmap fetch error:", err);
          setM7HeatmapLoading(false);
        });
    }
  }, [activeTab, jobId, m7HeatmapData, m7HeatmapLoading]);

  const loadEvents = useCallback(async () => {
    if (!jobId) return;
    setEventsLoading(true);
    try {
      const [m4Res, m5Res] = await Promise.allSettled([
        getAttentionEvents(jobId, { page_size: 100 }),
        getInteractionEvents(jobId, { page_size: 100 }),
      ]);

      const m4Events = m4Res.status === "fulfilled" ? m4Res.value.data || [] : [];
      const m5Events = m5Res.status === "fulfilled" ? m5Res.value.data || [] : [];

      const combined = [
        ...m4Events.map((e) => ({ ...e, sourceCategory: "ATTENTION" })),
        ...m5Events.map((e) => ({
          ...e,
          sourceCategory: "INTERACTION",
          attention_type: e.event_type,
          start_time: e.timestamp || e.start_time,
        })),
      ].sort((a, b) => (a.start_time || 0) - (b.start_time || 0));

      setEventsList(combined);
    } catch {
      setEventsList([]);
    } finally {
      setEventsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (activeTab === "logs" && eventsList.length === 0) {
      loadEvents();
    }
  }, [activeTab, eventsList.length, loadEvents]);

  const handleReEvaluate = async () => {
    if (reEvaluating || !jobId) return;
    setReEvaluating(true);
    setReEvalSuccess(false);
    try {
      invalidateUnifiedDataCache(jobId);
      if (heatmapBlobUrl) {
        URL.revokeObjectURL(heatmapBlobUrl);
        setHeatmapBlobUrl(null);
      }
      await reEvaluateAIJob(jobId);
      await loadAllData(true);
      await loadEvents();
      setReEvalSuccess(true);
      setTimeout(() => setReEvalSuccess(false), 4000);
    } catch (err) {
      console.error("Re-evaluation failed:", err);
      setError("Re-evaluation failed. Please verify pipeline outputs.");
    } finally {
      setReEvaluating(false);
    }
  };

  const contextValue = useMemo(() => ({
    job, jobId, isOpen, onClose,
    activeTab, setActiveTab,
    unifiedData, loading, error,
    reEvaluating, reEvalSuccess, handleReEvaluate,
    heatmapViewMode, setHeatmapViewMode, heatmapBlobUrl, heatmapImgLoading,
    m7HeatmapData, m7HeatmapLoading,
    eventsList, eventsLoading, eventSearch, setEventSearch, eventFilterType, setEventFilterType,
    matrixSearch, setMatrixSearch, matrixView, setMatrixView,
    reportViewMode, setReportViewMode, copied, setCopied,
    loadEvents
  }), [
    job, jobId, isOpen, onClose,
    activeTab, unifiedData, loading, error, reEvaluating, reEvalSuccess,
    heatmapViewMode, heatmapBlobUrl, heatmapImgLoading,
    m7HeatmapData, m7HeatmapLoading,
    eventsList, eventsLoading, eventSearch, eventFilterType,
    matrixSearch, matrixView,
    reportViewMode, copied
  ]);

  return (
    <UnifiedJobContext.Provider value={contextValue}>
      {children}
    </UnifiedJobContext.Provider>
  );
}

export function useUnifiedJobContext() {
  const ctx = useContext(UnifiedJobContext);
  if (!ctx) throw new Error("useUnifiedJobContext must be used within a UnifiedJobProvider");
  return ctx;
}
