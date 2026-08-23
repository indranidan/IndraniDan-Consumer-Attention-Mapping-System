import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getCameras,
  createCamera,
  updateCamera,
  deleteCamera,
  getStores,
  getZones,
  testCameraStream,
  getCameraSnapshot,
  getSyncCachedData,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import FormField from "../components/ui/FormField";
import StatusBadge from "../components/ui/StatusBadge";
import DeleteConfirm from "../components/ui/DeleteConfirm";
import FilterPanel from "../components/ui/FilterPanel";

const emptyFilters = { store_id: "", zone_id: "", status: "" };

export default function Cameras() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const storeIdFilter = searchParams.get("store_id") || "";

  const initialParams = { page: 1, page_size: 10 };
  if (storeIdFilter) initialParams.store_id = storeIdFilter;
  const cachedCamerasRes = getSyncCachedData("cameras", JSON.stringify(initialParams));
  const cachedStoresRes = getSyncCachedData("stores", JSON.stringify({}));

  const [cameras, setCameras] = useState(cachedCamerasRes?.data || []);
  const [stores, setStores] = useState(cachedStoresRes?.data || []);
  const [zones, setZones] = useState([]);
  const [filterZones, setFilterZones] = useState([]);
  const [loading, setLoading] = useState(!cachedCamerasRes);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(
    cachedCamerasRes
      ? parseInt(cachedCamerasRes?.headers?.["x-total-count"] || cachedCamerasRes?.data?.length || 0, 10)
      : 0
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [form, setForm] = useState({ store_id: storeIdFilter, zone_id: "", name: "", camera_source: "", location_description: "", status: "active" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Stream diagnostics & snapshot modal state
  const [testingId, setTestingId] = useState(null);
  const [streamHealth, setStreamHealth] = useState({});
  const [snapshotModal, setSnapshotModal] = useState(false);
  const [snapshotData, setSnapshotData] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  const fetchData = useCallback(async () => {
    if (!cameras.length) setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (storeIdFilter) params.store_id = storeIdFilter;
      if (search) params.search = search;
      Object.entries(filters).forEach(([key, val]) => { if (val) params[key] = val; });
      const [camerasRes, storesRes] = await Promise.all([getCameras(params), getStores()]);
      setCameras(camerasRes.data);
      setStores(storesRes.data);
      const total = parseInt(camerasRes.headers["x-total-count"] || camerasRes.data.length, 10);
      setTotalCount(total);
    } catch {
      if (!cameras.length) {
        setCameras([]);
        setTotalCount(0);
      }
    } finally {
      setLoading(false);
    }
  }, [search, storeIdFilter, filters, page, pageSize]);


  useEffect(() => { fetchData(); }, [fetchData]);

  // Cascade: form store → zones
  useEffect(() => {
    if (form.store_id) { getZones({ store_id: form.store_id }).then((res) => setZones(res.data)).catch(() => setZones([])); }
    else { setZones([]); }
  }, [form.store_id]);

  // Cascade: filter store → filter zones
  useEffect(() => {
    if (filters.store_id) { getZones({ store_id: filters.store_id }).then((res) => setFilterZones(res.data)).catch(() => setFilterZones([])); }
    else { setFilterZones([]); }
  }, [filters.store_id]);

  const filterConfig = [
    { key: "store_id", label: "Store", type: "select", placeholder: "All Stores",
      options: stores.map((s) => ({ value: s.id, label: `${s.name} (${s.store_code})` })) },
    { key: "zone_id", label: "Zone", type: "select", placeholder: "All Zones",
      options: filterZones.map((z) => ({ value: z.id, label: z.name })) },
    { key: "status", label: "Status", type: "select", placeholder: "All Statuses",
      options: [
        { value: "active", label: "Active" },
        { value: "inactive", label: "Inactive" },
        { value: "maintenance", label: "Maintenance" },
      ] },
  ];

  const handleSearchChange = (val) => { setSearch(val); setPage(1); };
  const handleFilterChange = (key, value) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "store_id") next.zone_id = "";
      return next;
    });
    setPage(1);
  };
  const handleFilterReset = () => { setFilters(emptyFilters); setPage(1); };
  const handlePageSizeChange = (newSize) => { setPageSize(newSize); setPage(1); };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => { const next = { ...p, [name]: value }; if (name === "store_id") next.zone_id = ""; return next; });
  };

  const openCreate = () => { setEditingCamera(null); setForm({ store_id: storeIdFilter || (stores[0]?.id || ""), zone_id: "", name: "", camera_source: "", location_description: "", status: "active" }); setError(""); setModalOpen(true); };
  const openEdit = (camera) => { setEditingCamera(camera); setForm({ store_id: camera.store_id, zone_id: camera.zone_id || "", name: camera.name || "", camera_source: camera.camera_source || "", location_description: camera.location_description || "", status: camera.status || "active" }); setError(""); setModalOpen(true); };

  const handleTestStream = async (cam) => {
    setTestingId(cam.id);
    try {
      const res = await testCameraStream(cam.id);
      setStreamHealth((prev) => ({ ...prev, [cam.id]: res.data }));
    } catch (err) {
      setStreamHealth((prev) => ({
        ...prev,
        [cam.id]: { status: "OFFLINE", message: "Failed to connect to stream." },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleViewSnapshot = async (cam) => {
    setSnapshotLoading(true);
    setSnapshotData(null);
    setSnapshotModal(true);
    try {
      const res = await getCameraSnapshot(cam.id);
      setSnapshotData(res.data);
    } catch (err) {
      setSnapshotData({
        error: err.response?.data?.detail || "Could not capture live frame snapshot.",
        camera_name: cam.name,
      });
    } finally {
      setSnapshotLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = { ...form, zone_id: form.zone_id || null };
      if (editingCamera) { await updateCamera(editingCamera.id, { zone_id: payload.zone_id, name: payload.name, camera_source: payload.camera_source, location_description: payload.location_description, status: payload.status }); }
      else { await createCamera(payload); }
      setModalOpen(false); fetchData();
    } catch (err) { setError(err.response?.data?.detail || "An error occurred."); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try { await deleteCamera(deleteTarget.id); setDeleteTarget(null); fetchData(); }
    catch (err) { setError(err.response?.data?.detail || "Failed to delete."); }
    finally { setDeleting(false); }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in pb-12">
      <PageHeader title="Cameras" description="Manage surveillance cameras and live stream connectivity in your stores"
        actionLabel="Add Camera" onAction={openCreate} showAction={canWrite}
        icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>}
      />

      <DataTable columns={["Camera", "Source", "Stream Health", "Store & Zone", "Status", "Actions"]}
        data={cameras} loading={loading} searchValue={search} onSearchChange={handleSearchChange}
        searchPlaceholder="Search cameras..." emptyTitle="No cameras found"
        page={page} pageSize={pageSize} totalCount={totalCount} onPageChange={setPage} onPageSizeChange={handlePageSizeChange}
        filterSlot={<FilterPanel filters={filterConfig} values={filters} onChange={handleFilterChange} onReset={handleFilterReset} />}
        renderRow={(camera) => {
          const health = streamHealth[camera.id];
          const isTesting = testingId === camera.id;

          return (
            <tr key={camera.id} className="hover:bg-gray-800/30 transition-colors">
              <td className="px-5 py-4">
                <p className="text-sm font-medium text-white">{camera.name}</p>
                {camera.location_description && <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">{camera.location_description}</p>}
              </td>
              <td className="px-5 py-4">
                <span className="inline-flex px-2 py-0.5 rounded-md bg-gray-800/50 text-xs font-mono text-cyan-400 truncate max-w-[180px]">
                  {camera.camera_source}
                </span>
              </td>
              <td className="px-5 py-4">
                {isTesting ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-ping" />
                    Probing stream...
                  </span>
                ) : health ? (
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
                      health.status === "ONLINE"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${health.status === "ONLINE" ? "bg-emerald-400" : "bg-red-400"}`} />
                    {health.status} {health.latency_ms !== undefined ? `(${health.latency_ms}ms)` : ""}
                  </span>
                ) : (
                  <span className="text-[11px] text-gray-500 font-mono">Not Tested</span>
                )}
              </td>
              <td className="px-5 py-4">
                <p className="text-sm text-gray-300">{camera.store_name || "—"}</p>
                <p className="text-xs text-gray-500">{camera.zone_name || "No Zone"}</p>
              </td>
              <td className="px-5 py-4"><StatusBadge status={camera.status} /></td>
              <td className="px-5 py-4">
                <div className="flex items-center gap-1">
                  {/* Test Stream Button */}
                  <button
                    onClick={() => handleTestStream(camera)}
                    disabled={isTesting}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all disabled:opacity-50"
                    title="Ping & Test Stream Health"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </button>

                  {/* Preview Snapshot Button */}
                  <button
                    onClick={() => handleViewSnapshot(camera)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                    title="Capture Live Snapshot Preview"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>

                  {canWrite && (
                    <>
                      <button onClick={() => openEdit(camera)} className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all" title="Edit">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                      </button>
                      <button onClick={() => setDeleteTarget(camera)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Delete">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          );
        }}
      />

      {/* Snapshot Preview Modal */}
      <Modal isOpen={snapshotModal} onClose={() => setSnapshotModal(false)} title="Live Camera Frame Snapshot" maxWidth="max-w-2xl">
        <div className="space-y-4">
          {snapshotLoading ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400 space-y-3">
              <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs">Connecting to stream & grabbing frame snapshot...</p>
            </div>
          ) : snapshotData?.error ? (
            <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl text-center space-y-2">
              <p className="text-red-400 font-semibold text-sm">❌ Stream Capture Error</p>
              <p className="text-xs text-gray-400">{snapshotData.error}</p>
            </div>
          ) : snapshotData?.image_data ? (
            <div className="space-y-3">
              <div className="rounded-2xl overflow-hidden border border-gray-800 bg-black aspect-video flex items-center justify-center">
                <img src={snapshotData.image_data} alt="Camera snapshot" className="w-full h-full object-contain" />
              </div>
              <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
                <span>Camera: {snapshotData.camera_name}</span>
                <span>Captured: {new Date(snapshotData.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ) : null}

          <div className="pt-2 flex justify-end">
            <button
              onClick={() => setSnapshotModal(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-gray-800 hover:bg-gray-700 transition-all"
            >
              Close Preview
            </button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingCamera ? "Edit Camera" : "Create Camera"} maxWidth="max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">{error}</div>}
          {!editingCamera && (
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Store" name="store_id" required>
                <select name="store_id" value={form.store_id} onChange={handleChange} required className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                  <option value="">Select store</option>
                  {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </FormField>
              <FormField label="Zone (Optional)" name="zone_id">
                <select name="zone_id" value={form.zone_id} onChange={handleChange} className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                  <option value="">No zone assigned</option>
                  {zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
                </select>
              </FormField>
            </div>
          )}
          {editingCamera && (
            <FormField label="Zone (Optional)" name="zone_id">
              <select name="zone_id" value={form.zone_id} onChange={handleChange} className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                <option value="">No zone assigned</option>
                {zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
              </select>
            </FormField>
          )}
          <FormField label="Camera Name" name="name" value={form.name} onChange={handleChange} required placeholder="e.g., Entrance Camera 1" />
          <FormField label="Camera Source" name="camera_source" value={form.camera_source} onChange={handleChange} required placeholder="e.g., rtsp://192.168.1.100:554/stream1" />
          <FormField label="Location Description" name="location_description" type="textarea" value={form.location_description} onChange={handleChange} placeholder="e.g., Mounted above main entrance" />
          <FormField label="Status" name="status">
            <select name="status" value={form.status} onChange={handleChange} className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="maintenance">Maintenance</option>
            </select>
          </FormField>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
              {saving && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {editingCamera ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <DeleteConfirm isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} loading={deleting} title="Delete Camera"
        message={`Are you sure you want to delete "${deleteTarget?.name}"?`} />
    </div>
  );
}

