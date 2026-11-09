import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const RECORDED = resolve(fileURLToPath(new URL(".", import.meta.url)), "../demo/recorded");

/** Dev only: serve the exported bundles in demo/recorded at /recorded, as the static build does. */
function recordedBundles(): Plugin {
  return {
    name: "recorded-bundles",
    configureServer(server) {
      server.middlewares.use("/recorded", (req, res, next) => {
        const rel = decodeURIComponent((req.url ?? "/").split("?")[0]);
        const file = resolve(RECORDED, "." + rel);
        if (!file.startsWith(RECORDED + sep) || !existsSync(file) || !statSync(file).isFile()) {
          next();
          return;
        }
        res.setHeader("Content-Type", "application/json");
        createReadStream(file).pipe(res);
      });
    },
  };
}

// OBSERVATORY=http://127.0.0.1:<port> proxies the live API of a running `observatory serve`.
const live = process.env.OBSERVATORY;

export default defineConfig({
  base: "./",
  plugins: [react(), recordedBundles()],
  server: live
    ? { proxy: { "/api": { target: live, changeOrigin: true } } }
    : undefined,
  build: { chunkSizeWarningLimit: 2000 },
});
