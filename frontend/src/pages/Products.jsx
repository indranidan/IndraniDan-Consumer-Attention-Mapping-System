/**
 * Products Page
 * ==============
 * Full CRUD management page for products.
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  getStores,
  getZones,
  getShelves,
  getSyncCachedData,
} from "../services/storeService";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Modal from "../components/ui/Modal";
import FormField from "../components/ui/FormField";
import DeleteConfirm from "../components/ui/DeleteConfirm";
import FilterPanel from "../components/ui/FilterPanel";

const emptyFilters = { store_id: "", zone_id: "", shelf_id: "", category: "", brand: "", min_price: "", max_price: "" };

export default function Products() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const storeIdFilter = searchParams.get("store_id") || "";

  const initialParams = { page: 1, page_size: 10 };
  if (storeIdFilter) initialParams.store_id = storeIdFilter;
  const cachedProductsRes = getSyncCachedData("products", JSON.stringify(initialParams));
  const cachedStoresRes = getSyncCachedData("stores", JSON.stringify({}));

  const [products, setProducts] = useState(cachedProductsRes?.data || []);
  const [stores, setStores] = useState(cachedStoresRes?.data || []);
  const [zones, setZones] = useState([]);
  const [shelves, setShelves] = useState([]);
  const [filterZones, setFilterZones] = useState([]);
  const [filterShelves, setFilterShelves] = useState([]);
  const [loading, setLoading] = useState(!cachedProductsRes);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(
    cachedProductsRes
      ? parseInt(cachedProductsRes?.headers?.["x-total-count"] || cachedProductsRes?.data?.length || 0, 10)
      : 0
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [form, setForm] = useState({ store_id: storeIdFilter, zone_id: "", shelf_id: "", name: "", sku: "", brand: "", category: "", price: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const userRole = typeof user?.role === "object" ? user.role.role_name : user?.role;
  const canWrite = ["Administrator", "Store Manager"].includes(userRole);

  const fetchData = useCallback(async () => {
    if (!products.length) setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (storeIdFilter) params.store_id = storeIdFilter;
      if (search) params.search = search;
      Object.entries(filters).forEach(([key, val]) => { if (val !== "" && val !== null && val !== undefined) params[key] = val; });
      const [productsRes, storesRes] = await Promise.all([getProducts(params), getStores()]);
      setProducts(productsRes.data);
      setStores(storesRes.data);
      const total = parseInt(productsRes.headers["x-total-count"] || productsRes.data.length, 10);
      setTotalCount(total);
    } catch {
      if (!products.length) {
        setProducts([]);
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

  // Cascade: form zone → shelves
  useEffect(() => {
    if (form.zone_id) { getShelves({ zone_id: form.zone_id }).then((res) => setShelves(res.data)).catch(() => setShelves([])); }
    else { setShelves([]); }
  }, [form.zone_id]);

  // Cascade: filter store → filter zones
  useEffect(() => {
    if (filters.store_id) { getZones({ store_id: filters.store_id }).then((res) => setFilterZones(res.data)).catch(() => setFilterZones([])); }
    else { setFilterZones([]); }
  }, [filters.store_id]);

  // Cascade: filter zone → filter shelves
  useEffect(() => {
    if (filters.zone_id) { getShelves({ zone_id: filters.zone_id }).then((res) => setFilterShelves(res.data)).catch(() => setFilterShelves([])); }
    else { setFilterShelves([]); }
  }, [filters.zone_id]);

  const filterConfig = [
    { key: "store_id", label: "Store", type: "select", placeholder: "All Stores",
      options: stores.map((s) => ({ value: s.id, label: `${s.name} (${s.store_code})` })) },
    { key: "zone_id", label: "Zone", type: "select", placeholder: "All Zones",
      options: filterZones.map((z) => ({ value: z.id, label: z.name })) },
    { key: "shelf_id", label: "Shelf", type: "select", placeholder: "All Shelves",
      options: filterShelves.map((sh) => ({ value: sh.id, label: `${sh.name} (${sh.shelf_code})` })) },
    { key: "category", label: "Category", type: "text", placeholder: "e.g., Dairy" },
    { key: "brand", label: "Brand", type: "text", placeholder: "e.g., Amul" },
    { key: "min_price", label: "Min Price", type: "number", placeholder: "0", min: 0 },
    { key: "max_price", label: "Max Price", type: "number", placeholder: "1000", min: 0 },
  ];

  const handleSearchChange = (val) => { setSearch(val); setPage(1); };
  const handleFilterChange = (key, value) => {
    setFilters((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "store_id") { next.zone_id = ""; next.shelf_id = ""; }
      if (key === "zone_id") { next.shelf_id = ""; }
      return next;
    });
    setPage(1);
  };
  const handleFilterReset = () => { setFilters(emptyFilters); setPage(1); };
  const handlePageSizeChange = (newSize) => { setPageSize(newSize); setPage(1); };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => {
      const next = { ...p, [name]: value };
      if (name === "store_id") { next.zone_id = ""; next.shelf_id = ""; }
      if (name === "zone_id") { next.shelf_id = ""; }
      return next;
    });
  };

  const openCreate = () => { setEditingProduct(null); setForm({ store_id: storeIdFilter || (stores[0]?.id || ""), zone_id: "", shelf_id: "", name: "", sku: "", brand: "", category: "", price: "", description: "" }); setError(""); setModalOpen(true); };
  const openEdit = (product) => { setEditingProduct(product); setForm({ store_id: product.store_id, zone_id: product.zone_id, shelf_id: product.shelf_id, name: product.name || "", sku: product.sku || "", brand: product.brand || "", category: product.category || "", price: product.price ?? "", description: product.description || "" }); setError(""); setModalOpen(true); };

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = { ...form, price: form.price !== "" ? parseFloat(form.price) : null };
      if (editingProduct) { await updateProduct(editingProduct.id, { name: payload.name, sku: payload.sku, brand: payload.brand, category: payload.category, price: payload.price, description: payload.description }); }
      else { await createProduct(payload); }
      setModalOpen(false); fetchData();
    } catch (err) { setError(err.response?.data?.detail || "An error occurred."); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try { await deleteProduct(deleteTarget.id); setDeleteTarget(null); fetchData(); }
    catch (err) { setError(err.response?.data?.detail || "Failed to delete."); }
    finally { setDeleting(false); }
  };

  const formatPrice = (price) => price != null ? `$${parseFloat(price).toFixed(2)}` : "—";

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <PageHeader title="Products" description="Manage products placed on shelves"
        actionLabel="Add Product" onAction={openCreate} showAction={canWrite}
        icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>}
      />

      <DataTable columns={canWrite ? ["Product", "SKU", "Brand", "Shelf", "Price", "Actions"] : ["Product", "SKU", "Brand", "Shelf", "Price"]}
        data={products} loading={loading} searchValue={search} onSearchChange={handleSearchChange}
        searchPlaceholder="Search by name, SKU, brand, or category..." emptyTitle="No products found"
        page={page} pageSize={pageSize} totalCount={totalCount} onPageChange={setPage} onPageSizeChange={handlePageSizeChange}
        filterSlot={<FilterPanel filters={filterConfig} values={filters} onChange={handleFilterChange} onReset={handleFilterReset} />}
        renderRow={(product) => (
          <tr key={product.id} className="hover:bg-gray-800/30 transition-colors">
            <td className="px-5 py-4">
              <p className="text-sm font-medium text-white">{product.name}</p>
              {product.category && <p className="text-xs text-gray-500 mt-0.5">{product.category}</p>}
            </td>
            <td className="px-5 py-4"><span className="inline-flex px-2 py-0.5 rounded-md bg-gray-800/50 text-xs font-mono text-violet-400">{product.sku}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{product.brand || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm text-gray-300">{product.shelf_name || "—"}</span></td>
            <td className="px-5 py-4"><span className="text-sm font-medium text-emerald-400">{formatPrice(product.price)}</span></td>
            {canWrite && (
              <td className="px-5 py-4">
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(product)} className="p-1.5 rounded-lg text-gray-400 hover:text-violet-400 hover:bg-violet-500/10 transition-all" title="Edit">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                  </button>
                  <button onClick={() => setDeleteTarget(product)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Delete">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </td>
            )}
          </tr>
        )}
      />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingProduct ? "Edit Product" : "Create Product"} maxWidth="max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">{error}</div>}
          {!editingProduct && (
            <div className="grid grid-cols-3 gap-4">
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
              <FormField label="Shelf" name="shelf_id" required>
                <select name="shelf_id" value={form.shelf_id} onChange={handleChange} required className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all">
                  <option value="">Select shelf</option>
                  {shelves.map((sh) => <option key={sh.id} value={sh.id}>{sh.name}</option>)}
                </select>
              </FormField>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Product Name" name="name" value={form.name} onChange={handleChange} required placeholder="e.g., Coca-Cola 500ml" />
            <FormField label="SKU" name="sku" value={form.sku} onChange={handleChange} required placeholder="e.g., SKU-CC-500" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <FormField label="Brand" name="brand" value={form.brand} onChange={handleChange} placeholder="e.g., Coca-Cola" />
            <FormField label="Category" name="category" value={form.category} onChange={handleChange} placeholder="e.g., Beverages" />
            <FormField label="Price" name="price" type="number" value={form.price} onChange={handleChange} placeholder="0.00" />
          </div>
          <FormField label="Description" name="description" type="textarea" value={form.description} onChange={handleChange} placeholder="Optional description..." />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 transition-all">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
              {saving && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {editingProduct ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </Modal>

      <DeleteConfirm isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} loading={deleting} title="Delete Product"
        message={`Are you sure you want to delete "${deleteTarget?.name}"?`} />
    </div>
  );
}
