import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (
              id.includes("react-dom") ||
              id.includes("react-router-dom") ||
              id.includes("react-hook-form") ||
              id.includes("/react/") ||
              id.includes("\\react\\")
            ) {
              return "vendor-react";
            }
            if (id.includes("chart.js") || id.includes("react-chartjs-2")) {
              return "vendor-charts";
            }
            if (id.includes("recharts") || id.includes("d3-") || id.includes("victory-vendor")) {
              return "vendor-recharts";
            }
            if (id.includes("axios")) {
              return "vendor-axios";
            }
          }
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/docs": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/redoc": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/openapi.json": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
