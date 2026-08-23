/**
 * Zones Page
 * ===========
 * Full CRUD management page for store zones.
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getZones,
  createZone,
  updateZone,
  deleteZone,
  getStores,
  getSyncCachedData,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import FormField from "../components/ui/FormField";
import DeleteConfirm from "../components/ui/DeleteConfirm";
import FilterPanel from "../components/ui/FilterPanel";

const emptyFilters = { store_id: "", name: "" };

export default function Zones() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const storeIdFilter = searchParams.get("store_id") || "";
  
  const initialParams = { page: 1, page_size: 10 };
  if (storeIdFilter) initialParams.store_id = storeIdFilter;
  const cachedZonesRes = getSyncCachedData("zones", JSON.stringify(initialParams));
  const cachedStoresRes = getSyncCachedData("stores", JSON.stringify({}));

  const [zones, setZones] = useState(cachedZonesRes?.data || []);
  const [stores, setStores] = useState(cachedStoresRes?.data || []);
  const [loading, setLoading] = useState(!cachedZonesRes);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(
    cachedZonesRes
      ? parseInt(cachedZonesRes?.headers?.["x-total-count"] || cachedZonesRes?.data?.length || 0, 10)
      : 0
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editingZone, setEditingZone] = useState(null);
  const [form, setForm] = useState({ store_id: storeIdFilter, name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  const fetchData = useCallback(async () => {
    if (!zones.length) setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (storeIdFilter) params.store_id = storeIdFilter;
      if (search) params.search = search;
      Object.entries(filters).forEach(([key, val]) => { if (val) params[key] = val; });
      const [zonesRes, storesRes] = await Promise.all([getZones(params), getStores()]);
      setZones(zonesRes.data);
      setStores(storesRes.data);
      const total = parseInt(zonesRes.headers["x-total-count"] || zonesRes.data.length, 10);
      setTotalCount(total);
    } catch {
      if (!zones.length) {
        setZones([]);
        setTotalCount(0);
      }
    }
    finally { setLoading(false); }
  }, [search, storeIdFilter, filters, page, pageSize]);


  useEffect(() => { fetchData(); }, [fetchData]);

  const filterConfig = [
    { key: "store_id", label: "Store", type: "select", placeholder: "All Stores",
      options: stores.map((s) => ({ value: s.id, label: `${s.name} (${s.store_code})` })) },
    { key: "name", label: "Zone Name", type: "text", placeholder: "Filter by name..." },
  ];

  const handleSearchChange = (val) => { setSearch(val); setPage(1); };
  const handleFilterChange = (key, value) => { setFilters((prev) => ({ ...prev, [key]: value })); setPage(1); };
  const handleFilterReset = () => { setFilters(emptyFilters); setPage(1); };
  const handlePageSizeChange = (newSize) => { setPageSize(newSize); setPage(1); };
  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const openCreate = () => { setEditingZone(null); setForm({ store_id: storeIdFilter || (stores[0]?.id || ""), name: "", description: "" }); setError(""); setModalOpen(true); };
  const openEdit = (zone) => { setEditingZone(zone); setForm({ store_id: zone.store_id, name: zone.name || "", description: zone.description || "" }); setError(""); setModalOpen(true); };

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      if (editingZone) { await updateZone(editingZone.id, { name: form.name, description: form.description }); }
      else { await createZone(form); }
      setModalOpen(false); fetchData();
    } catch (err) { setError(err.response?.data?.detail || "An error occurred."); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try { await deleteZone(deleteTarget.id); setDeleteTarget(null); fetchData(); }
    catch (err) { setError(err.response?.data?.detail || "Failed to delete."); }
    finally { setDeleting(false); }
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <PageHeader title="Zones" description="Manage logical areas within your stores" actionLabel="Add Zone" onAction={openCreate} showAction={canWrite}
        icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" /></svg>}
      />

      <DataTable columns={canWrite ? ["Zone", "Store", "Shelves", "Actions"] : ["Zone", "Store", "Shelves"]} data={zones} loading={loading} searchValue={search} onSearchChange={handleSearchChange}
        searchPlaceholder="Search zones..." emptyTitle="No zones found" emptyDescription="Create your first zone to organize your store layout."
        page={page} pageSize={pageSize} totalCount={totalCount} onPageChange={setPage} onPageSizeChange={handlePageSizeChange}
        filterSlot={<FilterPanel filters={filterConfig} values={filters} onChange={handleFilterChange} onReset={handleFilterReset} />}
        renderRow={(zone) => (
          <tr key={zone.id} className="hover:bg-gray-800/30 transition-colors">
            <td className="px-5 py-4">
              <p className="text-sm font-medium text-white">{zone.name}</p>
              {zone.description && <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[250px]">{zone.description}</p>}
            </td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{zone.store_name || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-400">{zone.shelf_count}</span></td>
            {canWrite && (
              <td className="px-5 py-4">
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(zone)} className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all" title="Edit">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  </button>
                  <button onClick={() => setDeleteTarget(zone)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Delete">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </td>
            )}
          </tr>
        )}
      />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingZone ? "Edit Zone" : "Create Zone"}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">{error}</div>}
          {!editingZone && (
            <FormField label="Store" name="store_id" required>
              <select name="store_id" value={form.store_id} onChange={handleChange} required className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                <option value="">Select a store</option>
                {stores.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.store_code})</option>)}
              </select>
            </FormField>
          )}
          <FormField label="Zone Name" name="name" value={form.name} onChange={handleChange} required placeholder="e.g., Entrance Zone" />
          <FormField label="Description" name="description" type="textarea" value={form.description} onChange={handleChange} placeholder="Optional description..." />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
              {saving && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {editingZone ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <DeleteConfirm isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} loading={deleting} title="Delete Zone"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This will also delete all shelves and products in this zone.`} />
    </div>
  );
}
