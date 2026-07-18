import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const root = resolve("dashboard");
const port = Number(process.env.PORT || 4173);
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
};
const vendorFiles = {
  "/vendor/pdf.mjs": resolve("node_modules/pdfjs-dist/build/pdf.mjs"),
  "/vendor/pdf.worker.mjs": resolve("node_modules/pdfjs-dist/build/pdf.worker.mjs"),
};
const username = process.env.APP_USERNAME;
const password = process.env.APP_PASSWORD;
const isRender = Boolean(process.env.RENDER);

function authorized(request) {
  if (!username || !password) return !isRender;
  const header = request.headers.authorization || "";
  if (!header.startsWith("Basic ")) return false;
  try {
    const [givenUser, ...parts] = Buffer.from(header.slice(6), "base64").toString("utf8").split(":");
    return givenUser === username && parts.join(":") === password;
  } catch {
    return false;
  }
}

createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url || "/", "http://localhost").pathname);
  if (pathname === "/healthz") {
    response.statusCode = 200;
    response.setHeader("Content-Type", "text/plain; charset=utf-8");
    response.setHeader("Cache-Control", "no-store");
    return response.end("ok");
  }
  if (!authorized(request)) {
    response.statusCode = username && password ? 401 : 503;
    response.setHeader("WWW-Authenticate", 'Basic realm="Private Credit Report Studio", charset="UTF-8"');
    response.setHeader("Cache-Control", "no-store");
    return response.end(username && password ? "Authentication required" : "Set APP_USERNAME and APP_PASSWORD in Render");
  }

  const safe = normalize(pathname).replace(/^(\.\.(\/|\\|$))+/, "");
  let file = vendorFiles[pathname] || join(root, safe === "/" ? "index.html" : safe);
  if (!vendorFiles[pathname] && (!file.startsWith(root) || !existsSync(file) || statSync(file).isDirectory())) file = join(root, "index.html");
  if (!existsSync(file)) {
    response.statusCode = 404;
    return response.end("Not Found");
  }
  response.setHeader("Content-Type", types[extname(file)] || "application/octet-stream");
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; worker-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
  response.setHeader("Referrer-Policy", "no-referrer");
  response.setHeader("X-Frame-Options", "DENY");
  createReadStream(file).pipe(response);
}).listen(port, "0.0.0.0", () => console.log(`Credit Report Studio: http://localhost:${port}`));
