import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./render-dist/", import.meta.url));
const port = Number(process.env.PORT || 4173);
const types = { ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".ico": "image/x-icon", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml", ".wasm": "application/wasm", ".woff2": "font/woff2" };

createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url || "/", "http://localhost").pathname);
  const requested = normalize(pathname).replace(/^(\.\.(\/|\\|$))+/, "");
  let file = join(root, requested);
  if (!file.startsWith(root) || !existsSync(file) || statSync(file).isDirectory()) file = join(root, "index.html");
  response.setHeader("Content-Type", types[extname(file)] || "application/octet-stream");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Cache-Control", extname(file) === ".html" ? "no-cache" : "public, max-age=31536000, immutable");
  if (request.method === "HEAD") return response.end();
  createReadStream(file).pipe(response);
}).listen(port, "0.0.0.0", () => console.log(`Dialogue Lantern running on port ${port}`));
