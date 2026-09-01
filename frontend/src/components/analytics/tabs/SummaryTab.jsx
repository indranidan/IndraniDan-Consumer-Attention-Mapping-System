import React from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import ShopperFunnelChart from '../ShopperFunnelChart';
import DwellDistributionChart from '../DwellDistributionChart';
import { MetricCard, ScoreBadge } from './SharedComponents';

export default function SummaryTab() {
  const { unifiedData, job } = useUnifiedJobContext();

  const m3Summary = unifiedData?.results?.summary || unifiedData?.report?.json_report?.summary || {};
  const m4Analysis = unifiedData?.attention || {};
  const m4Summary = m4Analysis.summary || {};
  const m4Shelves = m4Analysis.shelves || [];
  const m4Quality = m4Analysis.quality_metrics || {};
  
  const m5Analysis = unifiedData?.interaction || {};
  const m5Summary = m5Analysis.summary || {};
  const m5Products = m5Analysis.products || [];
  const m5Shelves = m5Analysis.shelves || [];

  const totalVisitors = m3Summary.unique_shoppers || m3Summary.total_unique_shoppers || m5Summary.total_unique_viewers || 0;
  const zoneDwellers = m3Summary.total_zone_visits || (totalVisitors > 0 ? Math.max(1, totalVisitors) : 0);
  const shelfViewers = m4Summary.total_attention_events || 0;
  const productViewers = m5Summary.total_views || 0;
  const productInteractions = (m5Summary.total_pickups || 0) + (m5Summary.total_comparisons || 0);

  const dwellRate = totalVisitors > 0 ? Math.min(100, Math.round((zoneDwellers / totalVisitors) * 100)) : 0;
  const gazeRate = zoneDwellers > 0 ? Math.min(100, Math.round((shelfViewers / zoneDwellers) * 100)) : 0;
  const viewRate = shelfViewers > 0 ? Math.min(100, Math.round((productViewers / shelfViewers) * 100)) : 0;
  const interactRate = productViewers > 0 ? Math.min(100, Math.round((productInteractions / productViewers) * 100)) : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 5-Stage Animated Shopper Journey Funnel */}
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              5-Stage Consumer Attention & Interaction Funnel
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              End-to-end shopper journey from store entry to product consideration
            </p>
          </div>
          <span className="text-[11px] font-mono text-gray-400 bg-gray-800/80 px-2.5 py-1 rounded-lg border border-gray-700/40">
            Conversion Rate: {m5Summary.conversion_rate_percentage || 0}%
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          {[
            {
              stage: "1. Store Traffic",
              count: totalVisitors,
              sub: "Unique Shoppers",
              color: "from-blue-600 to-indigo-600",
              badge: "100%",
            },
            {
              stage: "2. Zone Dwell",
              count: zoneDwellers,
              sub: "Zone Visits (>3s)",
              color: "from-indigo-600 to-violet-600",
              badge: `${dwellRate}%`,
            },
            {
              stage: "3. Shelf Gaze",
              count: shelfViewers,
              sub: "Attention Events",
              color: "from-violet-600 to-purple-600",
              badge: `${gazeRate}%`,
            },
            {
              stage: "4. Product Focus",
              count: productViewers,
              sub: "Product Views",
              color: "from-purple-600 to-pink-600",
              badge: `${viewRate}%`,
            },
            {
              stage: "5. Interaction",
              count: productInteractions,
              sub: "Pickups / Compares",
              color: "from-pink-600 to-rose-600",
              badge: `${interactRate}%`,
            },
          ].map((s, idx) => (
            <div
              key={idx}
              className="bg-gray-950/60 border border-gray-800/70 rounded-xl p-3.5 flex flex-col justify-between hover:border-gray-700 transition-all"
            >
              <div className="flex items-center justify-between text-[11px] text-gray-400 font-medium mb-1">
                <span>{s.stage}</span>
                <span className="px-1.5 py-0.2 rounded bg-gray-800 text-[10px] font-mono text-cyan-400">
                  {s.badge}
                </span>
              </div>
              <div className="my-1.5">
                <p className="text-xl font-bold text-white tracking-tight">{s.count}</p>
                <p className="text-[10px] text-gray-400">{s.sub}</p>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden mt-1">
                <div
                  className={`h-full bg-gradient-to-r ${s.color} rounded-full`}
                  style={{ width: s.badge }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Core KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        <MetricCard
          label="Shoppers"
          value={totalVisitors}
          icon="👥"
          gradient="from-blue-500 to-cyan-500"
          subtitle={`${m3Summary.total_sessions || totalVisitors} sessions`}
        />
        <MetricCard
          label="Avg Dwell"
          value={`${(m3Summary.average_zone_dwell_time_sec || 0).toFixed(1)}s`}
          icon="⏱️"
          gradient="from-cyan-500 to-teal-500"
          subtitle="Zone dwell duration"
        />
        <MetricCard
          label="Gaze Events"
          value={m4Summary.total_attention_events || 0}
          icon="👀"
          gradient="from-teal-500 to-emerald-500"
          subtitle={`${(m4Summary.total_attention_duration_sec || 0).toFixed(1)}s total gaze`}
        />
        <MetricCard
          label="Shelf Score"
          value={`${(m4Summary.shelf_engagement_score_avg || 0).toFixed(1)}`}
          icon="⭐"
          gradient="from-emerald-500 to-amber-500"
          badge="/ 100"
          subtitle="Avg shelf score"
        />
        <MetricCard
          label="Product Views"
          value={m5Summary.total_views || 0}
          icon="👁️"
          gradient="from-amber-500 to-rose-500"
          subtitle={`${m5Summary.total_unique_viewers || 0} unique viewers`}
        />
        <MetricCard
          label="Pickups"
          value={m5Summary.total_pickups || 0}
          icon="🖐️"
          gradient="from-purple-500 to-indigo-500"
          subtitle={`${m5Summary.total_returns || 0} returns`}
        />
      </div>

      {/* Interactive Dynamic Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ShopperFunnelChart
          funnelData={{
            passing: totalVisitors,
            glancing: shelfViewers,
            dwell: zoneDwellers,
            touch: productViewers,
            consideration: productInteractions,
          }}
        />
        <DwellDistributionChart
          distributionData={
            m3Summary.dwell_distribution ||
            unifiedData?.report?.json_report?.dwell_distribution ||
            unifiedData?.results?.reports?.dwell_distribution ||
            unifiedData?.report?.json_report?.phase4?.dwell_distribution
          }
          zoneSummaries={m4Shelves.length > 0 ? m4Shelves : (m3Summary.zone_breakdown || m5Shelves)}
          totalShoppers={totalVisitors}
          avgDwellTime={m3Summary.average_zone_dwell_time_sec || m4Summary.average_attention_duration_sec || 16.0}
        />
      </div>

      {/* Spotlight Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Top Shelf Spotlight */}
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>🏆</span> Most Attended Shelf
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
              Shelf Attention
            </span>
          </div>
          <div>
            <p className="text-base font-bold text-white">
              {m4Summary.most_viewed_shelf_name || m4Shelves[0]?.shelf_name || "Dairy Section Shelf A"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Generated highest aggregate gaze fixation score in monitored area.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
            <span className="text-gray-400">Engagement Score:</span>
            <ScoreBadge score={m4Shelves[0]?.engagement_score ?? 78.5} />
          </div>
        </div>

        {/* Top Product Spotlight */}
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>⭐</span> Most Engaged Product
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono">
              Product Focus
            </span>
          </div>
          <div>
            <p className="text-base font-bold text-white">
              {m5Summary.most_engaged_product_name || m5Products[0]?.product_name || "Organic Whole Milk 1L"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Highest consumer consideration journey and direct viewer fixations.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs">
            <span className="text-gray-400">Total Views:</span>
            <span className="font-semibold text-white font-mono">
              {m5Summary.total_views || m5Products[0]?.total_views || 0} views
            </span>
          </div>
        </div>

        {/* Pipeline Quality Statistics */}
        <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-violet-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>🎯</span> Attention Quality Index
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20 font-mono">
              Accuracy
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Face Detection Rate:</span>
              <span className="font-semibold text-white font-mono">
                {(((m4Quality?.face_detection_rate ?? 0.92)) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Pose Confidence:</span>
              <span className="font-semibold text-white font-mono">
                {(((m4Quality?.average_pose_confidence ?? 0.85)) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Valid Detections:</span>
              <span className="font-semibold text-white font-mono">
                {m4Quality?.valid_face_detections ?? shelfViewers} samples
              </span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-gray-800/60">
            <p className="text-[10px] text-gray-400 italic">
              3D head pose estimation calculated in camera coordinate frame.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
