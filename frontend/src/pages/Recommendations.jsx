/**
 * Recommendations Page
 * =====================
 * Dedicated Merchandising & Prescriptive Optimization page.
 * Allows selecting store/job and exploring Module 9 recommendations and what-if simulations.
 */

import { useState, useEffect } from "react";
import { getStores, getAIJobs } from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import RecommendationsDashboard from "../components/recommendations/RecommendationsDashboard";

export default function Recommendations() {
  const [stores, setStores] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [selectedJob, setSelectedJob] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [storesRes, jobsRes] = await Promise.all([
          getStores(),
          getAIJobs(),
        ]);
        const storeList = storesRes.data || [];
        const completedJobs = (jobsRes.data || []).filter((j) => j.status === "COMPLETED");

        setStores(storeList);
        setJobs(completedJobs);

        if (completedJobs.length > 0) {
          setSelectedJob(completedJobs[0].id);
          setSelectedStore(completedJobs[0].store_id || (storeList[0]?.id || ""));
        } else if (storeList.length > 0) {
          setSelectedStore(storeList[0].id);
        }
      } catch (err) {
        console.error("Failed to load initial stores and jobs:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleStoreChange = (e) => {
    const sId = e.target.value;
    setSelectedStore(sId);
    const storeJobs = jobs.filter((j) => j.store_id === sId);
    if (storeJobs.length > 0) {
      setSelectedJob(storeJobs[0].id);
    } else {
      setSelectedJob("");
    }
  };

  const filteredJobs = selectedStore
    ? jobs.filter((j) => j.store_id === selectedStore)
    : jobs;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Merchandising & Recommendations"
        subtitle="Prescriptive AI decision engine for shelf tier rebalancing, opportunity swaps, and friction intervention."
      />

      {/* Selectors */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/60 rounded-2xl p-4 flex flex-wrap items-center gap-4">
        <div>
          <label className="block text-[11px] font-medium text-gray-400 mb-1">
            Filter by Store
          </label>
          <select
            value={selectedStore}
            onChange={handleStoreChange}
            className="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50"
          >
            <option value="">All Stores</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                🏬 {s.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-medium text-gray-400 mb-1">
            Select Analysis Job
          </label>
          <select
            value={selectedJob}
            onChange={(e) => setSelectedJob(e.target.value)}
            disabled={filteredJobs.length === 0}
            className="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50 disabled:opacity-50 min-w-[240px]"
          >
            {filteredJobs.length === 0 ? (
              <option value="">No completed jobs found</option>
            ) : (
              filteredJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  📷 {j.camera_name || "Camera"} — {new Date(j.created_at).toLocaleDateString()}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Recommendations Dashboard */}
      {selectedJob ? (
        <RecommendationsDashboard jobId={selectedJob} storeId={selectedStore} />
      ) : (
        <div className="bg-gray-900/40 border border-gray-800/60 rounded-2xl p-12 text-center">
          <span className="text-4xl">🎬</span>
          <h4 className="text-sm font-bold text-white mt-3">No AI Analysis Job Selected</h4>
          <p className="text-xs text-gray-400 mt-1 max-w-md mx-auto">
            Please run an AI Analytics pipeline job or select a completed job above to view prescriptive recommendations.
          </p>
        </div>
      )}
    </div>
  );
}
