import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Vite server proxies API calls to the Python backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist" },
});
