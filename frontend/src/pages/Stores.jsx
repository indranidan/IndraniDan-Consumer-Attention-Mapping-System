/**
 * Stores Page
 * ============
 * Full CRUD management page for retail stores.
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getStores,
  createStore,
  updateStore,
  deleteStore,
  getSyncCachedData,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import FormField from "../components/ui/FormField";
import StatusBadge from "../components/ui/StatusBadge";
import DeleteConfirm from "../components/ui/DeleteConfirm";
import FilterPanel from "../components/ui/FilterPanel";

const emptyForm = {
  name: "",
  store_code: "",
  address: "",
  city: "",
  state: "",
  country: "",
  postal_code: "",
  description: "",
  status: "active",
};

const emptyFilters = {
  name: "",
  store_code: "",
  city: "",
  state: "",
  country: "",
  status: "",
};

const filterConfig = [
  { key: "name", label: "Store Name", type: "text", placeholder: "e.g. Flagship" },
  { key: "store_code", label: "Store Code", type: "text", placeholder: "e.g. NYC-01" },
  { key: "city", label: "City", type: "text", placeholder: "e.g. New York" },
  { key: "state", label: "State", type: "text", placeholder: "e.g. NY" },
  { key: "country", label: "Country", type: "text", placeholder: "e.g. USA" },
  {
    key: "status",
    label: "Status",
    type: "select",
    options: [
      { value: "active", label: "Active" },
      { value: "inactive", label: "Inactive" },
    ],
  },
];

export default function Stores() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const cachedStoresRes = getSyncCachedData("stores", JSON.stringify({ page: 1, page_size: 10 }));
  const [stores, setStores] = useState(cachedStoresRes?.data || []);
  const [loading, setLoading] = useState(!cachedStoresRes);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(
    cachedStoresRes
      ? parseInt(cachedStoresRes?.headers?.["x-total-count"] || cachedStoresRes?.data?.length || 0, 10)
      : 0
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStore, setEditingStore] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);
  const canDelete = userRole === "Administrator";
  const showActions = canWrite || canDelete;

  const fetchStores = useCallback(async () => {
    if (!stores.length) setLoading(true);
    try {

      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      // Merge active filters
      Object.entries(filters).forEach(([key, val]) => {
        if (val) params[key] = val;
      });
      const res = await getStores(params);
      const items = Array.isArray(res?.data) ? res.data : (res?.data?.items || []);
      setStores(items);
      const headerTotal = res?.headers?.["x-total-count"] || res?.headers?.["X-Total-Count"];
      const total = headerTotal !== undefined && headerTotal !== null ? parseInt(headerTotal, 10) : items.length;
      setTotalCount(isNaN(total) ? items.length : total);
    } catch {
      setStores([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [search, filters, page, pageSize]);

  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  const handleSearchChange = (val) => {
    setSearch(val);
    setPage(1);
  };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const handleFilterReset = () => {
    setFilters(emptyFilters);
    setPage(1);
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setPage(1);
  };

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const openCreate = () => {
    setEditingStore(null);
    setForm(emptyForm);
    setError("");
    setModalOpen(true);
  };

  const openEdit = (store) => {
    setEditingStore(store);
    setForm({
      name: store.name || "",
      store_code: store.store_code || "",
      address: store.address || "",
      city: store.city || "",
      state: store.state || "",
      country: store.country || "",
      postal_code: store.postal_code || "",
      description: store.description || "",
      status: store.status || "active",
    });
    setError("");
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editingStore) {
        await updateStore(editingStore.id, form);
      } else {
        await createStore(form);
      }
      setModalOpen(false);
      fetchStores();
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteStore(deleteTarget.id);
      setDeleteTarget(null);
      fetchStores();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <PageHeader
        title="Stores"
        description="Manage your retail store locations"
        actionLabel="Add Store"
        onAction={openCreate}
        showAction={canWrite}
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
        }
      />

      <DataTable
        columns={showActions ? ["Store", "Code", "Location", "Status", "Zones", "Actions"] : ["Store", "Code", "Location", "Status", "Zones"]}
        data={stores}
        loading={loading}
        searchValue={search}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search by name, code, city, or country..."
        emptyTitle="No stores found"
        emptyDescription="Create your first store to get started."
        page={page}
        pageSize={pageSize}
        totalCount={totalCount}
        onPageChange={setPage}
        onPageSizeChange={handlePageSizeChange}
        filterSlot={
          <FilterPanel
            filters={filterConfig}
            values={filters}
            onChange={handleFilterChange}
            onReset={handleFilterReset}
          />
        }
        renderRow={(store) => (
          <tr
            key={store.id}
            className="hover:bg-gray-800/30 transition-colors cursor-pointer"
            onClick={() => navigate(`/stores/${store.id}`)}
          >
            <td className="px-5 py-4">
              <div>
                <p className="text-sm font-medium text-white">{store.name}</p>
                {store.description && (
                  <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">{store.description}</p>
                )}
              </div>
            </td>
            <td className="px-5 py-4">
              <span className="inline-flex px-2 py-0.5 rounded-md bg-gray-800/50 text-xs font-mono text-violet-400">
                {store.store_code}
              </span>
            </td>
            <td className="px-5 py-4">
              <p className="text-sm text-gray-300">
                {[store.city, store.state, store.country].filter(Boolean).join(", ") || "—"}
              </p>
            </td>
            <td className="px-5 py-4">
              <StatusBadge status={store.status} />
            </td>
            <td className="px-5 py-4">
              <span className="text-sm text-gray-400">{store.zone_count}</span>
            </td>
            {showActions && (
              <td className="px-5 py-4" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center gap-1">
                  {canWrite && (
                    <button
                      onClick={() => openEdit(store)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
                      title="Edit store"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                  )}
                  {canDelete && (
                    <button
                      onClick={() => setDeleteTarget(store)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
                      title="Delete store"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  )}
                </div>
              </td>
            )}
          </tr>
        )}
      />

      {/* Create / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingStore ? "Edit Store" : "Create Store"}
        maxWidth="max-w-xl"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Store Name" name="name" value={form.name} onChange={handleChange} required placeholder="e.g., Downtown Store" />
            <FormField label="Store Code" name="store_code" value={form.store_code} onChange={handleChange} required placeholder="e.g., STORE-001" />
          </div>

          <FormField label="Address" name="address" value={form.address} onChange={handleChange} placeholder="Street address" />

          <div className="grid grid-cols-2 gap-4">
            <FormField label="City" name="city" value={form.city} onChange={handleChange} placeholder="e.g., New York" />
            <FormField label="State" name="state" value={form.state} onChange={handleChange} placeholder="e.g., NY" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Country" name="country" value={form.country} onChange={handleChange} placeholder="e.g., USA" />
            <FormField label="Postal Code" name="postal_code" value={form.postal_code} onChange={handleChange} placeholder="e.g., 10001" />
          </div>

          <FormField label="Description" name="description" type="textarea" value={form.description} onChange={handleChange} placeholder="Optional description..." />

          <FormField label="Status" name="status">
            <select
              id="status"
              name="status"
              value={form.status}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </FormField>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {editingStore ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation */}
      <DeleteConfirm
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleting}
        title="Delete Store"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This will also delete all its zones, shelves, products, and cameras.`}
      />
    </div>
  );
}
