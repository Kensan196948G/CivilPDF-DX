import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const apiTarget = (process.env.VITE_API_URL || "http://localhost:8000")
  .replace(/\/+$/, "")
  .replace(/\/api\/v1$/, "");

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    host: true,
    // Cloudflare Tunnel 経由の公開ホスト名 (deploy/civilpdf-cloudflared.service)
    allowedHosts: ["civilpdf.mirai-dx-platform.com"],
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 400,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("react-dom") || id.includes("react/"))
              return "vendor";
            if (id.includes("react-router")) return "router";
            if (id.includes("@tanstack")) return "query";
            if (id.includes("zustand")) return "state";
            if (id.includes("axios")) return "http";
            if (id.includes("jose") || id.includes("jwt")) return "auth";
          }
        },
      },
    },
  },
});
