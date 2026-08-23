/**
 * Store Details Page
 * ===================
 * Shows store information with tabbed views for zones, shelves, products, and cameras.
 */

import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getStoreById, getZones, getShelves } from "../services/storeService";
import StatusBadge from "../components/ui/StatusBadge";
import StoreFloorplanMap from "../components/store/StoreFloorplanMap";

export default function StoreDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [store, setStore] = useState(null);
  const [zones, setZones] = useState([]);
  const [shelves, setShelves] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStore = useCallback(async () => {
    setLoading(true);
    try {
      const [storeRes, zonesRes, shelvesRes] = await Promise.allSettled([
        getStoreById(id),
        getZones({ store_id: id }),
        getShelves({ store_id: id }),
      ]);
      if (storeRes.status === "fulfilled") {
        setStore(storeRes.value.data);
      } else {
        navigate("/stores");
      }
      if (zonesRes.status === "fulfilled") setZones(zonesRes.value.data);
      if (shelvesRes.status === "fulfilled") setShelves(shelvesRes.value.data);
    } catch {
      navigate("/stores");
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchStore();
  }, [fetchStore]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!store) return null;

  const infoItems = [
    { label: "Store Code", value: store.store_code, mono: true },
    { label: "Address", value: store.address },
    { label: "City", value: store.city },
    { label: "State", value: store.state },
    { label: "Country", value: store.country },
    { label: "Postal Code", value: store.postal_code },
    { label: "Zones", value: store.zone_count || zones.length },
    { label: "Cameras", value: store.camera_count },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in pb-12">
      {/* Back button */}
      <button
        onClick={() => navigate("/stores")}
        className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Stores
      </button>

      {/* Store Header */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-3xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-violet-500/20 flex-shrink-0">
              <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{store.name}</h1>
              {store.description && (
                <p className="text-sm text-gray-400 mt-1">{store.description}</p>
              )}
            </div>
          </div>
          <StatusBadge status={store.status} />
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          {infoItems.map((item) => (
            <div key={item.label} className="px-4 py-3 rounded-xl bg-gray-800/30 border border-gray-800/50">
              <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-1">{item.label}</p>
              <p className={`text-sm font-medium text-white ${item.mono ? "font-mono text-violet-400" : ""}`}>
                {item.value || "—"}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── 2D Store Floorplan Mapping ─────────────────────────────── */}
      <StoreFloorplanMap
        store={store}
        zones={zones}
        shelves={shelves}
        onSelectShelf={(s) => navigate(`/shelves?store_id=${store.id}`)}
      />

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          {
            label: "Zones",
            count: store.zone_count || zones.length,
            path: `/zones?store_id=${store.id}`,
            gradient: "from-emerald-500 to-teal-600",
            icon: (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
                />
              </svg>
            ),
          },
          {
            label: "Shelves",
            count: shelves.length,
            path: `/shelves?store_id=${store.id}`,
            gradient: "from-amber-500 to-orange-600",
            icon: (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
            ),
          },
          {
            label: "Products",
            path: `/products?store_id=${store.id}`,
            gradient: "from-pink-500 to-rose-600",
            icon: (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            ),
          },
          {
            label: "Cameras",
            count: store.camera_count,
            path: `/cameras?store_id=${store.id}`,
            gradient: "from-cyan-500 to-blue-600",
            icon: (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            ),
          },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => navigate(item.path)}
            className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/50 rounded-2xl p-5 hover:border-gray-700/50 transition-all duration-300 group text-left"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-gray-500 uppercase tracking-wider">{item.label}</span>
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${item.gradient} flex items-center justify-center text-white shadow-lg opacity-80 group-hover:opacity-100 transition-opacity`}>
                {item.icon}
              </div>
            </div>
            <p className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
              View {item.label} {item.count !== undefined ? `(${item.count})` : ""} →
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

