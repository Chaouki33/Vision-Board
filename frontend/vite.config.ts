import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // Adresse de l'API (modifiable pour lancer une seconde instance de test).
        target: process.env.VISIONBOARD_API_URL ?? "http://127.0.0.1:8000",
        // API arrêtée : réponse 502 explicite (l'interface affiche alors un message clair).
        configure: (proxy) => {
          proxy.on("error", (_err, _req, res) => {
            if ("writeHead" in res && !res.headersSent) {
              res.writeHead(502, { "Content-Type": "text/plain" });
              res.end("API indisponible");
            }
          });
        },
      },
    },
  },
});
