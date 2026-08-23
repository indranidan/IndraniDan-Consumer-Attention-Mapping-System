/**
 * Archetype Behavioral Radar Chart Component
 * ============================================
 * Interactive Chart.js 5-axis radar chart displaying normalized shopper feature profiles:
 * - Path Efficiency
 * - Gaze Alternation
 * - Dwell / Transit Ratio
 * - Brand Concentration
 * - Promo Deviation Sensitivity
 */

import React, { useMemo } from "react";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import { Radar } from "react-chartjs-2";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const ARCHETYPE_DEFAULTS = {
  EXPLORER: [25, 45, 35, 20, 80],
  QUICK_BUYER: [90, 15, 20, 40, 10],
  COMPARISON_SHOPPER: [40, 95, 85, 30, 40],
  IMPULSE_BUYER: [50, 60, 65, 35, 95],
  BRAND_LOYAL: [75, 25, 70, 95, 15],
};

const ARCHETYPE_COLORS = {
  EXPLORER: { border: "rgb(59, 130, 246)", bg: "rgba(59, 130, 246, 0.25)" },
  QUICK_BUYER: { border: "rgb(245, 158, 11)", bg: "rgba(245, 158, 11, 0.25)" },
  COMPARISON_SHOPPER: { border: "rgb(168, 85, 247)", bg: "rgba(168, 85, 247, 0.25)" },
  IMPULSE_BUYER: { border: "rgb(244, 63, 94)", bg: "rgba(244, 63, 94, 0.25)" },
  BRAND_LOYAL: { border: "rgb(16, 185, 129)", bg: "rgba(16, 185, 129, 0.25)" },
};

export default function ArchetypeRadarChart({ activeArchetype = "EXPLORER", featureVector }) {
  const radarData = useMemo(() => {
    const labels = [
      "Path Efficiency",
      "Gaze Alternation",
      "Dwell Intensity",
      "Brand Focus",
      "Promo Sensitivity",
    ];

    let values = ARCHETYPE_DEFAULTS[activeArchetype] || ARCHETYPE_DEFAULTS.EXPLORER;

    if (featureVector) {
      values = [
        Math.min(100, Math.round((featureVector.path_efficiency || 0) * 100)),
        Math.min(100, Math.round((featureVector.gaze_alternation_rate || 0) * 100)),
        Math.min(100, Math.round((featureVector.dwell_to_transit_ratio || 0) * 25)),
        Math.min(100, Math.round((featureVector.brand_concentration || 0) * 100)),
        Math.min(100, Math.round((featureVector.promo_deviation_count || 0) * 20)),
      ];
    }

    const theme = ARCHETYPE_COLORS[activeArchetype] || ARCHETYPE_COLORS.EXPLORER;

    return {
      labels,
      datasets: [
        {
          label: `${activeArchetype.replace("_", " ")} Profile`,
          data: values,
          backgroundColor: theme.bg,
          borderColor: theme.border,
          borderWidth: 2,
          pointBackgroundColor: theme.border,
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: theme.border,
          pointRadius: 4,
        },
      ],
    };
  }, [activeArchetype, featureVector]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top",
        labels: {
          color: "#cbd5e1",
          font: { size: 12, weight: "600" },
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        titleColor: "#f8fafc",
        bodyColor: "#94a3b8",
        borderColor: "rgba(51, 65, 85, 0.7)",
        borderWidth: 1,
        padding: 10,
      },
    },
    scales: {
      r: {
        angleLines: {
          color: "rgba(51, 65, 85, 0.5)",
        },
        grid: {
          color: "rgba(51, 65, 85, 0.35)",
        },
        pointLabels: {
          color: "#94a3b8",
          font: { size: 11, weight: "500" },
        },
        ticks: {
          display: false,
          min: 0,
          max: 100,
        },
      },
    },
    animation: {
      duration: 600,
      easing: "easeOutCubic",
    },
  };

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-white tracking-wide uppercase flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
          5-Axis Behavioral Feature Profile
        </h4>
      </div>
      <div className="h-64 relative">
        <Radar data={radarData} options={options} />
      </div>
    </div>
  );
}
