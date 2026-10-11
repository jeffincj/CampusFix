// Vite config for the officials' dashboard.
// Dev:   npm run dev   -> http://localhost:5173/dashboard/  (API calls proxied to Django)
// Build: npm run build -> files go to backend/frontend_dist/dashboard/, served by Django at /dashboard/
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // In production the built files are Django static files.
  base: command === "build" ? "/static/dashboard/" : "/dashboard/",
  build: {
    outDir: "../backend/frontend_dist/dashboard",
    emptyOutDir: true,
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Send /api requests to Django (in Docker: http://backend:8000)
      "/api": process.env.VITE_API_PROXY || "http://localhost:8000",
    },
  },
}));
