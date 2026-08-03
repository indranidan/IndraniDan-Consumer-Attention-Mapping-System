/**
 * Cameras Page
 * =============
 * Full CRUD management page for cameras.
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getCameras, createCamera, updateCamera, deleteCamera, getStores, getZones } from "../services/storeService";
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
  const [cameras, setCameras] = useState([]);
  const [stores, setStores] = useState([]);
  const [zones, setZones] = useState([]);
  const [filterZones, setFilterZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [form, setForm] = useState({ store_id: storeIdFilter, zone_id: "", name: "", camera_source: "", location_description: "", status: "active" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  const fetchData = useCallback(async () => {
    setLoading(true);
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
    } catch { setCameras([]); setTotalCount(0); }
    finally { setLoading(false); }
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
    <div className="max-w-6xl mx-auto animate-fade-in">
      <PageHeader title="Cameras" description="Manage surveillance cameras in your stores"
        actionLabel="Add Camera" onAction={openCreate} showAction={canWrite}
        icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>}
      />

      <DataTable columns={canWrite ? ["Camera", "Source", "Store", "Zone", "Status", "Actions"] : ["Camera", "Source", "Store", "Zone", "Status"]}
        data={cameras} loading={loading} searchValue={search} onSearchChange={handleSearchChange}
        searchPlaceholder="Search cameras..." emptyTitle="No cameras found"
        page={page} pageSize={pageSize} totalCount={totalCount} onPageChange={setPage} onPageSizeChange={handlePageSizeChange}
        filterSlot={<FilterPanel filters={filterConfig} values={filters} onChange={handleFilterChange} onReset={handleFilterReset} />}
        renderRow={(camera) => (
          <tr key={camera.id} className="hover:bg-gray-800/30 transition-colors">
            <td className="px-5 py-4">
              <p className="text-sm font-medium text-white">{camera.name}</p>
              {camera.location_description && <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">{camera.location_description}</p>}
            </td>
            <td className="px-5 py-4"><span className="inline-flex px-2 py-0.5 rounded-md bg-gray-800/50 text-xs font-mono text-cyan-400 truncate max-w-[180px]">{camera.camera_source}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{camera.store_name || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{camera.zone_name || "—"}</span></td>
            <td className="px-5 py-4"><StatusBadge status={camera.status} /></td>
            {canWrite && (
              <td className="px-5 py-4">
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(camera)} className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all" title="Edit">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  </button>
                  <button onClick={() => setDeleteTarget(camera)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Delete">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </td>
            )}
          </tr>
        )}
      />

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
