import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The API base is configurable via VITE_API_BASE_URL. In dev we proxy /api to
// the FastAPI backend so cookies are same-origin.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
