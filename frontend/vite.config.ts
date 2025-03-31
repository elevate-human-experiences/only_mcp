import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import basicSsl from "@vitejs/plugin-basic-ssl";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), basicSsl()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 4096,
    https: {},
    proxy: {
      "/api": {
        target: "http://backend:8080", // changed to backend service name
      },
      "/.well-known/oauth-authorization-server": {
        target: "http://backend:8080",
      },
    },
  },
});
