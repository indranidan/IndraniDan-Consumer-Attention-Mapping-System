/**
 * Shelves Page
 * =============
 * Full CRUD management page for shelves.
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getShelves,
  createShelf,
  updateShelf,
  deleteShelf,
  getStores,
  getZones,
  getSyncCachedData,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import FormField from "../components/ui/FormField";
import DeleteConfirm from "../components/ui/DeleteConfirm";
import FilterPanel from "../components/ui/FilterPanel";
import StoreFloorplanMap from "../components/store/StoreFloorplanMap";

const emptyFilters = { store_id: "", zone_id: "", category: "", shelf_code: "" };

export default function Shelves() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const storeIdFilter = searchParams.get("store_id") || "";

  const initialParams = { page: 1, page_size: 10 };
  if (storeIdFilter) initialParams.store_id = storeIdFilter;
  const cachedShelvesRes = getSyncCachedData("shelves", JSON.stringify(initialParams));
  const cachedStoresRes = getSyncCachedData("stores", JSON.stringify({}));
  const cachedZonesRes = getSyncCachedData("zones", JSON.stringify(storeIdFilter ? { store_id: storeIdFilter } : {}));

  const [shelves, setShelves] = useState(cachedShelvesRes?.data || []);
  const [stores, setStores] = useState(cachedStoresRes?.data || []);
  const [zones, setZones] = useState(cachedZonesRes?.data || []);
  const [filterZones, setFilterZones] = useState([]);
  const [loading, setLoading] = useState(!cachedShelvesRes);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(
    cachedShelvesRes
      ? parseInt(cachedShelvesRes?.headers?.["x-total-count"] || cachedShelvesRes?.data?.length || 0, 10)
      : 0
  );
  const [viewTab, setViewTab] = useState("table"); // table | floorplan

  const [modalOpen, setModalOpen] = useState(false);
  const [editingShelf, setEditingShelf] = useState(null);
  const [form, setForm] = useState({ store_id: storeIdFilter, zone_id: "", name: "", shelf_code: "", category: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  const fetchData = useCallback(async () => {
    if (!shelves.length) setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (storeIdFilter) params.store_id = storeIdFilter;
      if (search) params.search = search;
      Object.entries(filters).forEach(([key, val]) => { if (val) params[key] = val; });
      const [shelvesRes, storesRes, allZonesRes] = await Promise.all([
        getShelves(params),
        getStores(),
        getZones(storeIdFilter ? { store_id: storeIdFilter } : {}),
      ]);
      const shelfItems = Array.isArray(shelvesRes?.data) ? shelvesRes.data : (shelvesRes?.data?.items || []);
      const storeItems = Array.isArray(storesRes?.data) ? storesRes.data : (storesRes?.data?.items || []);
      const zoneItems = Array.isArray(allZonesRes?.data) ? allZonesRes.data : (allZonesRes?.data?.items || []);
      setShelves(shelfItems);
      setStores(storeItems);
      setZones(zoneItems);
      const headerTotal = shelvesRes?.headers?.["x-total-count"] || shelvesRes?.headers?.["X-Total-Count"];
      const total = headerTotal !== undefined && headerTotal !== null ? parseInt(headerTotal, 10) : shelfItems.length;
      setTotalCount(isNaN(total) ? shelfItems.length : total);
    } catch {
      if (!shelves.length) {
        setShelves([]);
        setTotalCount(0);
      }
    } finally {
      setLoading(false);
    }
  }, [search, storeIdFilter, filters, page, pageSize]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch zones for form when store changes
  useEffect(() => {
    if (form.store_id) { getZones({ store_id: form.store_id }).then((res) => setZones(res.data)).catch(() => setZones([])); }
    else { setZones([]); }
  }, [form.store_id]);

  // Fetch zones for filter when filter store changes
  useEffect(() => {
    if (filters.store_id) { getZones({ store_id: filters.store_id }).then((res) => setFilterZones(res.data)).catch(() => setFilterZones([])); }
    else { setFilterZones([]); }
  }, [filters.store_id]);

  const filterConfig = [
    { key: "store_id", label: "Store", type: "select", placeholder: "All Stores",
      options: stores.map((s) => ({ value: s.id, label: `${s.name} (${s.store_code})` })) },
    { key: "zone_id", label: "Zone", type: "select", placeholder: "All Zones",
      options: filterZones.map((z) => ({ value: z.id, label: z.name })) },
    { key: "category", label: "Category", type: "text", placeholder: "e.g., Beverages" },
    { key: "shelf_code", label: "Shelf Code", type: "text", placeholder: "e.g., SH-001" },
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

  const openCreate = () => { setEditingShelf(null); setForm({ store_id: storeIdFilter || (stores[0]?.id || ""), zone_id: "", name: "", shelf_code: "", category: "", description: "" }); setError(""); setModalOpen(true); };
  const openEdit = (shelf) => { setEditingShelf(shelf); setForm({ store_id: shelf.store_id, zone_id: shelf.zone_id, name: shelf.name || "", shelf_code: shelf.shelf_code || "", category: shelf.category || "", description: shelf.description || "" }); setError(""); setModalOpen(true); };

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      if (editingShelf) { await updateShelf(editingShelf.id, { name: form.name, shelf_code: form.shelf_code, category: form.category, description: form.description }); }
      else { await createShelf(form); }
      setModalOpen(false); fetchData();
    } catch (err) { setError(err.response?.data?.detail || "An error occurred."); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try { await deleteShelf(deleteTarget.id); setDeleteTarget(null); fetchData(); }
    catch (err) { setError(err.response?.data?.detail || "Failed to delete."); }
    finally { setDeleting(false); }
  };

  const currentStoreObj = stores.find((s) => s.id === (filters.store_id || storeIdFilter)) || stores[0];

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <PageHeader title="Shelves" description="Manage shelving units within store zones"
          actionLabel="Add Shelf" onAction={openCreate} showAction={canWrite}
          icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>}
        />

        {/* View Switcher */}
        <div className="flex items-center bg-gray-900/80 p-1.5 rounded-2xl border border-gray-800 text-xs">
          <button
            onClick={() => setViewTab("table")}
            className={`px-3 py-1.5 rounded-xl font-medium transition-all ${
              viewTab === "table" ? "bg-violet-600 text-white shadow-lg" : "text-gray-400 hover:text-white"
            }`}
          >
            📋 Table View
          </button>
          <button
            onClick={() => setViewTab("floorplan")}
            className={`px-3 py-1.5 rounded-xl font-medium transition-all ${
              viewTab === "floorplan" ? "bg-violet-600 text-white shadow-lg" : "text-gray-400 hover:text-white"
            }`}
          >
            🏬 2D Floorplan Map
          </button>
        </div>
      </div>

      {viewTab === "floorplan" ? (
        <StoreFloorplanMap
          store={currentStoreObj}
          zones={zones}
          shelves={shelves}
          onSelectShelf={(s) => openEdit(s)}
        />
      ) : (
        <DataTable columns={canWrite ? ["Shelf", "Code", "Zone", "Store", "Category", "Products", "Actions"] : ["Shelf", "Code", "Zone", "Store", "Category", "Products"]}
          data={shelves} loading={loading} searchValue={search} onSearchChange={handleSearchChange}
          searchPlaceholder="Search shelves..." emptyTitle="No shelves found"
          page={page} pageSize={pageSize} totalCount={totalCount} onPageChange={setPage} onPageSizeChange={handlePageSizeChange}
          filterSlot={<FilterPanel filters={filterConfig} values={filters} onChange={handleFilterChange} onReset={handleFilterReset} />}
          renderRow={(shelf) => (
            <tr key={shelf.id} className="hover:bg-gray-800/30 transition-colors">
            <td className="px-5 py-4"><p className="text-sm font-medium text-white">{shelf.name}</p></td>
            <td className="px-5 py-4"><span className="inline-flex px-2 py-0.5 rounded-md bg-gray-800/50 text-xs font-mono text-violet-400">{shelf.shelf_code}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{shelf.zone_name || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{shelf.store_name || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-400">{shelf.category || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-400">{shelf.product_count}</span></td>
            {canWrite && (
              <td className="px-5 py-4">
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(shelf)} className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all" title="Edit">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  </button>
                  <button onClick={() => setDeleteTarget(shelf)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Delete">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </td>
            )}
          </tr>
        )}
      />
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingShelf ? "Edit Shelf" : "Create Shelf"} maxWidth="max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">{error}</div>}
          {!editingShelf && (
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Store" name="store_id" required>
                <select name="store_id" value={form.store_id} onChange={handleChange} required className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                  <option value="">Select store</option>
                  {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </FormField>
              <FormField label="Zone" name="zone_id" required>
                <select name="zone_id" value={form.zone_id} onChange={handleChange} required className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                  <option value="">Select zone</option>
                  {zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
                </select>
              </FormField>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Shelf Name" name="name" value={form.name} onChange={handleChange} required placeholder="e.g., Shelf A-1" />
            <FormField label="Shelf Code" name="shelf_code" value={form.shelf_code} onChange={handleChange} required placeholder="e.g., SH-001" />
          </div>
          <FormField label="Category" name="category" value={form.category} onChange={handleChange} placeholder="e.g., Beverages" />
          <FormField label="Description" name="description" type="textarea" value={form.description} onChange={handleChange} placeholder="Optional description..." />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
              {saving && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {editingShelf ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <DeleteConfirm isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} loading={deleting} title="Delete Shelf"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This will also delete all products on this shelf.`} />
    </div>
  );
}
