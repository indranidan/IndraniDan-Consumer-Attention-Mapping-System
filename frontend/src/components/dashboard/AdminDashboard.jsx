/**
 * AdminDashboard – Platform governance & system health.
 * Sections: User Management, Platform Analytics,
 * Camera Management, System Monitoring.
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";

function KpiCard({ icon, label, value, sub, color = "text-white" }) {
  return (
    <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5">
      <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1.5">
        <span>{icon}</span>{label}
      </p>
      <p className={`text-2xl font-extrabold mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    COMPLETED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    PROCESSING: "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse",
    FAILED: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${styles[status] || "bg-gray-500/10 text-gray-400"}`}>
      {status}
    </span>
  );
}

export default function AdminDashboard({ analytics, stats, loading }) {
  const admin = analytics?.admin || {};
  const entities = admin.entity_counts || {};
  const cameraFleet = admin.camera_fleet || {};
  const pipeline = admin.pipeline_health || {};
  const recentJobs = admin.recent_jobs || [];
  const navigate = useNavigate();

  const [userInfo, setUserInfo] = useState(null);
  const [userLoading, setUserLoading] = useState(true);

  useEffect(() => {
    api.get("/api/users/")
      .then((res) => setUserInfo(res.data))
      .catch(() => setUserInfo(null))
      .finally(() => setUserLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const roleStats = userInfo?.role_stats || {};
  const userList = userInfo?.users || [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── 1. User Management ─────────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>👤</span> User Management
        </h2>
        {userLoading ? (
          <div className="bg-gray-900/60 border border-gray-800/80 rounded-2xl p-6 text-center text-gray-500 text-xs">Loading users…</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              <KpiCard icon="👥" label="Total Users" value={userInfo?.total || 0} />
              {Object.entries(roleStats).map(([role, count]) => (
                <KpiCard key={role} icon="🏷️" label={role} value={count} />
              ))}
            </div>
            <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400">
                      <th className="px-4 py-3 font-semibold">Name</th>
                      <th className="px-4 py-3 font-semibold">Email</th>
                      <th className="px-4 py-3 font-semibold">Role</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60">
                    {userList.slice(0, 8).map((u) => (
                      <tr key={u.id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-3 text-white font-medium">{u.full_name}</td>
                        <td className="px-4 py-3 text-gray-400">{u.email}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-violet-500/10 text-violet-400 border border-violet-500/20">{u.role}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${u.is_active ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20"}`}>
                            {u.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ── 2. Platform Analytics ───────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>📊</span> Platform Analytics
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { icon: "🏬", label: "Stores", count: entities.stores || stats?.stores || 0, path: "/stores" },
            { icon: "📍", label: "Zones", count: entities.zones || stats?.zones || 0, path: "/zones" },
            { icon: "📦", label: "Shelves", count: entities.shelves || stats?.shelves || 0, path: "/shelves" },
            { icon: "🏷️", label: "Products", count: entities.products || stats?.products || 0, path: "/products" },
            { icon: "📹", label: "Cameras", count: entities.cameras || stats?.cameras || 0, path: "/cameras" },
          ].map((e) => (
            <button
              key={e.label}
              onClick={() => navigate(e.path)}
              className="bg-gray-900/60 hover:bg-gray-800/60 border border-gray-800/80 rounded-2xl p-4 text-left transition-colors group"
            >
              <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1">{e.icon} {e.label}</p>
              <p className="text-xl font-extrabold text-white font-mono mt-1">{e.count}</p>
            </button>
          ))}
        </div>
      </section>

      {/* ── 3. Camera Management ────────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🎥</span> Camera Management
        </h2>
        <div className="grid grid-cols-3 gap-3">
          <KpiCard icon="✅" label="Active Cameras" value={cameraFleet.active || 0} color="text-emerald-400" />
          <KpiCard icon="⚠️" label="Offline" value={cameraFleet.offline || 0} color={cameraFleet.offline > 0 ? "text-rose-400" : "text-white"} />
          <KpiCard icon="📹" label="Total Fleet" value={cameraFleet.total || 0} />
        </div>
        <button
          onClick={() => navigate("/cameras")}
          className="mt-3 text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors"
        >
          Manage Cameras →
        </button>
      </section>

      {/* ── 4. System Monitoring ────────────────────────────────── */}
      <section>
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>⚡</span> System Monitoring — AI Pipeline
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <KpiCard icon="✅" label="Completed" value={pipeline.completed || 0} color="text-emerald-400" />
          <KpiCard icon="⏳" label="Processing" value={pipeline.processing || 0} color="text-blue-400" />
          <KpiCard icon="❌" label="Failed" value={pipeline.failed || 0} color={pipeline.failed > 0 ? "text-rose-400" : "text-white"} />
          <KpiCard icon="📈" label="Success Rate" value={`${pipeline.success_rate || 0}%`} color="text-emerald-400" />
        </div>

        {recentJobs.length > 0 && (
          <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400">
                    <th className="px-4 py-3 font-semibold">Camera</th>
                    <th className="px-4 py-3 font-semibold">Store</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold">Duration</th>
                    <th className="px-4 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {recentJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-800/30 transition-colors">
                      <td className="px-4 py-3 text-white font-medium">{job.camera_name}</td>
                      <td className="px-4 py-3 text-gray-400">{job.store_name}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 font-mono text-gray-400">{job.duration ? `${job.duration}s` : "—"}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => navigate("/ai-jobs")} className="text-violet-400 hover:text-violet-300 font-semibold">Inspect →</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
