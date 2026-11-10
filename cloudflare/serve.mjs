import { Miniflare } from "miniflare";
import fs from "node:fs";
const mf = new Miniflare({
  modules: true, scriptPath: "worker.js", script: fs.readFileSync("worker.js", "utf8"),
  compatibilityDate: "2026-10-01", kvNamespaces: ["DATA"], bindings: { ADMIN_PASSWORD: "uji-coba-123" },
  port: 8787, host: "127.0.0.1",
});
await mf.ready; console.log("READY"); setInterval(() => {}, 1 << 30);
