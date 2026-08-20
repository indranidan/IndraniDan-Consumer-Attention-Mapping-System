/**
 * AI Analytics Page
 * ==================
 * Manage AI analysis jobs and view consumer attention analytics.
 * Supports dummy/logical database cameras paired with local Video Files or Webcam input.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../hooks/useAuth";
import {
  getStores,
  getCameras,
  createAIJob,
  getAIJobs,
  stopAIJob,
  getAIJobResults,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import Modal from "../components/ui/Modal";
import Module4AttentionAnalytics from "../components/module4/Module4AttentionAnalytics";
import Module3TrackingAnalytics from "../components/module3/Module3TrackingAnalytics";


const STATUS_COLORS = {
  QUEUED: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  RUNNING: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  COMPLETED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  FAILED: "bg-red-500/10 text-red-400 border-red-500/20",
  STOPPED: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

function JobStatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${STATUS_COLORS[status] || STATUS_COLORS.STOPPED}`}
    >
      {(status === "RUNNING" || status === "QUEUED") && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      )}
      {status}
    </span>
  );
}

function InputTypeBadge({ inputType }) {
  const isWebcam = inputType === "WEBCAM";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
        isWebcam
          ? "bg-purple-500/10 text-purple-300 border-purple-500/20"
          : "bg-cyan-500/10 text-cyan-300 border-cyan-500/20"
      }`}
    >
      {isWebcam ? "📷 WEBCAM" : "🎬 VIDEO FILE"}
    </span>
  );
}

function MetricCard({ label, value, icon, gradient }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] text-gray-500 uppercase tracking-wider">
          {label}
        </span>
        <div
          className={`w-9 h-9 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-lg opacity-80`}
        >
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value ?? "—"}</p>
    </div>
  );
}

export default function AIAnalytics() {
  const { user } = useAuth();
  const userRole =
    typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  // Job list state
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Create job workflow state
  const [stores, setStores] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [selectedCamera, setSelectedCamera] = useState("");
  const [inputType, setInputType] = useState("VIDEO_FILE"); // "VIDEO_FILE" | "WEBCAM"
  const [selectedFile, setSelectedFile] = useState(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Webcam state
  const [webcamActive, setWebcamActive] = useState(false);
  const [webcamStream, setWebcamStream] = useState(null);
  const videoPreviewRef = useRef(null);
  const fileInputRef = useRef(null);

  // Results modal
  const [resultsModal, setResultsModal] = useState(false);
  const [resultsData, setResultsData] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [resultsTab, setResultsTab] = useState("module4"); // "module4" | "module3"


  // Error modal
  const [errorModal, setErrorModal] = useState(false);
  const [errorJob, setErrorJob] = useState(null);

  // Polling
  const pollRef = useRef(null);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await getAIJobs();
      setJobs(res.data);
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    getStores()
      .then((res) => setStores(res.data))
      .catch(() => setStores([]));
  }, [fetchJobs]);

  // Fetch cameras when store changes
  useEffect(() => {
    if (selectedStore) {
      getCameras({ store_id: selectedStore, status: "active" })
        .then((res) => setCameras(res.data))
        .catch(() => setCameras([]));
    } else {
      setCameras([]);
    }
    setSelectedCamera("");
  }, [selectedStore]);

  // Handle webcam video element stream attachment
  useEffect(() => {
    if (videoPreviewRef.current && webcamStream) {
      videoPreviewRef.current.srcObject = webcamStream;
    }
  }, [webcamStream]);

  // Cleanup webcam stream on unmount
  useEffect(() => {
    return () => {
      if (webcamStream) {
        webcamStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [webcamStream]);

  // Poll for active jobs
  useEffect(() => {
    const hasActive = jobs.some(
      (j) => j.status === "QUEUED" || j.status === "RUNNING"
    );
    if (hasActive) {
      pollRef.current = setInterval(fetchJobs, 5000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs, fetchJobs]);

  const startWebcam = async () => {
    try {
      setCreateError("");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      setWebcamStream(stream);
      setWebcamActive(true);
    } catch (err) {
      setCreateError(
        "Failed to access webcam. Please check browser camera permissions."
      );
    }
  };

  const stopWebcam = () => {
    if (webcamStream) {
      webcamStream.getTracks().forEach((track) => track.stop());
      setWebcamStream(null);
    }
    setWebcamActive(false);
    if (videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = null;
    }
  };

  const recordWebcamClip = (durationMs = 5000) => {
    return new Promise((resolve, reject) => {
      if (!webcamStream) {
        reject(new Error("Webcam stream is not active."));
        return;
      }
      try {
        const chunks = [];
        const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
          ? "video/webm;codecs=vp9"
          : "video/webm";
        const recorder = new MediaRecorder(webcamStream, { mimeType });
        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) chunks.push(e.data);
        };
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: "video/webm" });
          resolve(blob);
        };
        recorder.start();
        setTimeout(() => {
          if (recorder.state === "recording") {
            recorder.stop();
          }
        }, durationMs);
      } catch (err) {
        reject(err);
      }
    });
  };

  const handleCreateJob = async () => {
    if (!selectedStore) {
      setCreateError("Please select a store.");
      return;
    }
    if (!selectedCamera) {
      setCreateError("Please select a camera.");
      return;
    }

    if (inputType === "VIDEO_FILE") {
      if (!selectedFile) {
        setCreateError("Please select a video file.");
        return;
      }
      setCreating(true);
      setCreateError("");
      try {
        const formData = new FormData();
        formData.append("store_id", selectedStore);
        formData.append("camera_id", selectedCamera);
        formData.append("input_type", "VIDEO_FILE");
        formData.append("file", selectedFile);

        await createAIJob(formData);

        // Reset form
        setSelectedStore("");
        setSelectedCamera("");
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        fetchJobs();
      } catch (err) {
        setCreateError(
          err.response?.data?.detail || "Failed to create AI job."
        );
      } finally {
        setCreating(false);
      }
    } else if (inputType === "WEBCAM") {
      if (!webcamActive || !webcamStream) {
        setCreateError("Please click 'Start Camera' to activate webcam preview first.");
        return;
      }

      setCreating(true);
      setCreateError("");

      try {
        const recordedBlob = await recordWebcamClip(5000);
        const webcamFile = new File([recordedBlob], "webcam_recording.webm", {
          type: "video/webm",
        });

        const formData = new FormData();
        formData.append("store_id", selectedStore);
        formData.append("camera_id", selectedCamera);
        formData.append("input_type", "WEBCAM");
        formData.append("file", webcamFile);

        await createAIJob(formData);

        stopWebcam();
        setSelectedStore("");
        setSelectedCamera("");
        fetchJobs();
      } catch (err) {
        setCreateError(
          err.response?.data?.detail || err.message || "Failed to start webcam analysis."
        );
      } finally {
        setCreating(false);
      }
    }
  };

  const handleStop = async (jobId) => {
    try {
      await stopAIJob(jobId);
      fetchJobs();
    } catch {
      /* ignore */
    }
  };

  const handleViewResults = async (job) => {
    setSelectedJob(job);
    setResultsModal(true);
    setResultsLoading(true);
    try {
      const res = await getAIJobResults(job.id);
      setResultsData(res.data);
    } catch {
      setResultsData(null);
    } finally {
      setResultsLoading(false);
    }
  };

  const handleViewError = (job) => {
    setErrorJob(job);
    setErrorModal(true);
  };

  const formatDate = (d) => {
    if (!d) return "—";
    return new Date(d).toLocaleString();
  };

  const formatDuration = (start, end) => {
    if (!start || !end) return "—";
    const ms = new Date(end) - new Date(start);
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    return `${m}m ${s % 60}s`;
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <PageHeader
        title="AI Analytics"
        description="Run AI-powered consumer attention analysis on camera footage"
        icon={
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        }
      />

      {/* ── Create Job Panel ─────────────────────────────── */}
      {canWrite && (
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-6 mb-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <svg
              className="w-4 h-4 text-violet-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            Start New Analysis
          </h3>

          {/* Steps 1 & 2: Store & Camera */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                Step 1: Select Store
              </label>
              <select
                value={selectedStore}
                onChange={(e) => setSelectedStore(e.target.value)}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 transition-all"
              >
                <option value="">Choose Store...</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                Step 2: Select Logical Camera
              </label>
              <select
                value={selectedCamera}
                onChange={(e) => setSelectedCamera(e.target.value)}
                disabled={!selectedStore}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 transition-all disabled:opacity-50"
              >
                <option value="">
                  {selectedStore ? "Choose Camera..." : "Select a store first"}
                </option>
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Step 3: Input Source Selection */}
          <div className="mb-5">
            <label className="block text-xs font-medium text-gray-400 mb-2">
              Step 3: Select Input Source
            </label>
            <div className="flex gap-3 mb-4">
              <button
                type="button"
                onClick={() => {
                  setInputType("VIDEO_FILE");
                  stopWebcam();
                  setCreateError("");
                }}
                className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-medium border flex items-center justify-center gap-2 transition-all ${
                  inputType === "VIDEO_FILE"
                    ? "bg-violet-600/20 border-violet-500/50 text-white shadow-lg"
                    : "bg-gray-800/40 border-gray-700/40 text-gray-400 hover:text-white"
                }`}
              >
                <svg
                  className="w-4 h-4 text-violet-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
                Video File Mode
              </button>
              <button
                type="button"
                onClick={() => {
                  setInputType("WEBCAM");
                  setCreateError("");
                }}
                className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-medium border flex items-center justify-center gap-2 transition-all ${
                  inputType === "WEBCAM"
                    ? "bg-violet-600/20 border-violet-500/50 text-white shadow-lg"
                    : "bg-gray-800/40 border-gray-700/40 text-gray-400 hover:text-white"
                }`}
              >
                <svg
                  className="w-4 h-4 text-emerald-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
                Webcam Mode
              </button>
            </div>

            {/* VIDEO_FILE Upload Box */}
            {inputType === "VIDEO_FILE" && (
              <div className="bg-gray-800/30 border border-gray-700/40 rounded-xl p-4">
                <label className="block text-xs text-gray-400 mb-2">
                  Upload Sample Store Video Footage (.mp4, .avi, .mov, .mkv, .webm)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp4,.avi,.mov,.mkv,.webm,video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        setSelectedFile(e.target.files[0]);
                        setCreateError("");
                      }
                    }}
                    className="hidden"
                    id="video-upload-input"
                  />
                  <label
                    htmlFor="video-upload-input"
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-medium cursor-pointer transition-all flex items-center gap-2"
                  >
                    <svg
                      className="w-4 h-4 text-violet-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                      />
                    </svg>
                    Choose Video File
                  </label>
                  {selectedFile ? (
                    <div className="flex items-center gap-2 bg-gray-900/60 px-3 py-1.5 rounded-lg border border-gray-800 text-xs">
                      <span className="text-white font-medium truncate max-w-[240px]">
                        {selectedFile.name}
                      </span>
                      <span className="text-gray-500">
                        ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedFile(null);
                          if (fileInputRef.current) fileInputRef.current.value = "";
                        }}
                        className="text-red-400 hover:text-red-300 ml-1 font-bold"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs text-gray-500 italic">No video selected</span>
                  )}
                </div>
              </div>
            )}

            {/* WEBCAM Preview Box */}
            {inputType === "WEBCAM" && (
              <div className="bg-gray-800/30 border border-gray-700/40 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-gray-400 font-medium">
                    Webcam Live Preview
                  </span>
                  <div className="flex items-center gap-2">
                    {!webcamActive ? (
                      <button
                        type="button"
                        onClick={startWebcam}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all flex items-center gap-1.5"
                      >
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        Start Camera
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={stopWebcam}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all"
                      >
                        Stop Camera
                      </button>
                    )}
                  </div>
                </div>

                <div className="relative w-full aspect-video bg-gray-950 rounded-xl overflow-hidden border border-gray-800 flex items-center justify-center">
                  <video
                    ref={videoPreviewRef}
                    autoPlay
                    playsInline
                    muted
                    className={`w-full h-full object-cover ${webcamActive ? "block" : "hidden"}`}
                  />
                  {!webcamActive && (
                    <div className="text-center p-6">
                      <svg
                        className="w-10 h-10 text-gray-700 mx-auto mb-2"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      <p className="text-xs text-gray-500">Camera preview inactive</p>
                      <p className="text-[11px] text-gray-600 mt-1">
                        Click &apos;Start Camera&apos; above to enable browser webcam feed
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              onClick={handleCreateJob}
              disabled={!selectedStore || !selectedCamera || creating}
              className="px-6 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg"
            >
              {creating && (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
              </svg>
              Start AI Analysis
            </button>
          </div>

          {createError && (
            <div className="mt-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
              {createError}
            </div>
          )}
        </div>
      )}

      {/* ── Jobs Table ───────────────────────────────────── */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800/50">
          <h3 className="text-sm font-semibold text-white">Analysis Jobs</h3>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Loading jobs...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-gray-800/50 flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6 text-gray-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-400">
              No analysis jobs yet
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Select a store and camera above to start
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800/50">
                  {["Camera", "Type", "Store", "Status", "Created", "Duration", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-left text-[11px] font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/30">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="px-5 py-4">
                      <p className="text-sm font-medium text-white">
                        {job.camera_name || "—"}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px] font-mono">
                        {job.source}
                      </p>
                    </td>
                    <td className="px-5 py-4">
                      <InputTypeBadge inputType={job.input_type} />
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-300">
                      {job.store_name || "—"}
                    </td>
                    <td className="px-5 py-4">
                      <JobStatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-400">
                      {formatDate(job.created_at)}
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-400">
                      {formatDuration(job.started_at, job.completed_at)}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1">
                        {job.status === "COMPLETED" && (
                          <button
                            onClick={() => handleViewResults(job)}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 transition-all"
                          >
                            View Results
                          </button>
                        )}
                        {job.status === "FAILED" && (
                          <button
                            onClick={() => handleViewError(job)}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-all"
                          >
                            View Error
                          </button>
                        )}
                        {(job.status === "RUNNING" ||
                          job.status === "QUEUED") &&
                          canWrite && (
                            <button
                              onClick={() => handleStop(job.id)}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 transition-all"
                            >
                              Stop
                            </button>
                          )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Results Modal ────────────────────────────────── */}
      <Modal
        isOpen={resultsModal}
        onClose={() => {
          setResultsModal(false);
          setResultsData(null);
          setResultsTab("module4");
        }}
        title={`Analytics Results — ${selectedJob?.camera_name || ""}`}
        maxWidth="max-w-5xl"
      >
        {/* Module Switcher Tabs */}
        <div className="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
          <button
            type="button"
            onClick={() => setResultsTab("module4")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              resultsTab === "module4"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "bg-gray-800/40 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Module 4 — Attention Analysis Engine
          </button>
          <button
            type="button"
            onClick={() => setResultsTab("module3")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              resultsTab === "module3"
                ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                : "bg-gray-800/40 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Module 3 — Tracking & Movement Analytics
          </button>
        </div>

        {resultsTab === "module4" ? (
          <Module4AttentionAnalytics jobId={selectedJob?.id} job={selectedJob} />
        ) : (
          <Module3TrackingAnalytics jobId={selectedJob?.id} job={selectedJob} resultsData={resultsData} />
        )}
      </Modal>


      {/* ── Error Modal ──────────────────────────────────── */}
      <Modal
        isOpen={errorModal}
        onClose={() => {
          setErrorModal(false);
          setErrorJob(null);
        }}
        title="Job Error Details"
        maxWidth="max-w-2xl"
      >
        {errorJob && (
          <div className="space-y-4">
            <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400 font-medium mb-2">
                Job failed at {formatDate(errorJob.completed_at)}
              </p>
              <pre className="text-xs text-red-300/80 whitespace-pre-wrap font-mono max-h-60 overflow-y-auto">
                {errorJob.error_message || "No error details available."}
              </pre>
            </div>
            <div className="text-xs text-gray-500">
              <p>Camera: {errorJob.camera_name}</p>
              <p>Source: {errorJob.source}</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
