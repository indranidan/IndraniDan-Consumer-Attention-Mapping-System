/**
 * Shopper Funnel Chart Component
 * ================================
 * Interactive Chart.js conversion funnel visualizing the 5 retail stages:
 * Passing -> Glancing -> Dwell -> Touch -> Consideration.
 */

import React, { useMemo } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function ShopperFunnelChart({ funnelData }) {
  const { stages, dropoffs, labels, counts } = useMemo(() => {
    if (!funnelData) {
      return {
        stages: [],
        dropoffs: [],
        labels: ["Passing", "Glancing", "Dwell", "Touch", "Consideration"],
        counts: [0, 0, 0, 0, 0],
      };
    }

    const rawStages = [
      { name: "Passing", count: funnelData.passing ?? funnelData.stage_1_passing ?? 0 },
      { name: "Glancing", count: funnelData.glancing ?? funnelData.stage_2_glancing ?? 0 },
      { name: "Dwell", count: funnelData.dwell ?? funnelData.stage_3_dwell ?? 0 },
      { name: "Touch", count: funnelData.touch ?? funnelData.stage_4_touch ?? 0 },
      { name: "Consideration", count: funnelData.consideration ?? funnelData.stage_5_consideration ?? 0 },
    ];

    const countsList = rawStages.map((s) => s.count);
    const dropoffList = countsList.map((cnt, idx) => {
      if (idx === 0) return 100;
      const prev = countsList[idx - 1];
      return prev > 0 ? ((cnt / prev) * 100).toFixed(1) : 0;
    });

    return {
      stages: rawStages,
      dropoffs: dropoffList,
      labels: rawStages.map((s) => s.name),
      counts: countsList,
    };
  }, [funnelData]);

  const data = {
    labels,
    datasets: [
      {
        label: "Shopper Count",
        data: counts,
        backgroundColor: [
          "rgba(99, 102, 241, 0.8)",   // Indigo (Passing)
          "rgba(59, 130, 246, 0.8)",   // Blue (Glancing)
          "rgba(6, 182, 212, 0.8)",    // Cyan (Dwell)
          "rgba(16, 185, 129, 0.8)",   // Emerald (Touch)
          "rgba(245, 158, 11, 0.8)",   // Amber (Consideration)
        ],
        borderColor: [
          "rgba(99, 102, 241, 1)",
          "rgba(59, 130, 246, 1)",
          "rgba(6, 182, 212, 1)",
          "rgba(16, 185, 129, 1)",
          "rgba(245, 158, 11, 1)",
        ],
        borderWidth: 1.5,
        borderRadius: 8,
        barThickness: 28,
      },
    ],
  };

  const options = {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        titleColor: "#f8fafc",
        bodyColor: "#94a3b8",
        borderColor: "rgba(51, 65, 85, 0.7)",
        borderWidth: 1,
        padding: 12,
        boxPadding: 6,
        callbacks: {
          label: (context) => {
            const index = context.dataIndex;
            const count = context.raw;
            const firstCount = counts[0] || 1;
            const overallPct = ((count / firstCount) * 100).toFixed(1);
            const stepPct = dropoffs[index];
            return [
              ` Count: ${count} shoppers`,
              ` Step Retention: ${stepPct}%`,
              ` Funnel Conversion: ${overallPct}%`,
            ];
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: "rgba(51, 65, 85, 0.3)",
        },
        ticks: {
          color: "#94a3b8",
          font: { size: 11 },
        },
      },
      y: {
        grid: {
          display: false,
        },
        ticks: {
          color: "#f8fafc",
          font: { weight: "600", size: 12 },
        },
      },
    },
    animation: {
      duration: 800,
      easing: "easeOutQuart",
    },
  };

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-white tracking-wide uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            5-Stage Shopper Conversion Funnel
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Interactive drop-off and conversion rates across shopper engagement stages
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-400">Overall Conversion:</span>
          <span className="ml-2 text-sm font-bold font-mono text-amber-400">
            {counts[0] > 0 ? `${(((counts[4] || 0) / counts[0]) * 100).toFixed(1)}%` : "0.0%"}
          </span>
        </div>
      </div>
      <div className="h-64 relative">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
