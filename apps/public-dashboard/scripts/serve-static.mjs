import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";

const host = "127.0.0.1";
const port = 4173;
const root = resolve("out");
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function safePath(pathname) {
  const decoded = decodeURIComponent(pathname);
  const relative = normalize(decoded).replace(/^([/\\])+/, "");
  const candidate = join(root, relative);
  return candidate === root || candidate.startsWith(`${root}${sep}`) ? candidate : null;
}

async function resolveFile(pathname) {
  const candidate = safePath(pathname);
  if (!candidate) return null;

  try {
    const details = await stat(candidate);
    if (details.isDirectory()) return join(candidate, "index.html");
    return candidate;
  } catch {
    if (!extname(candidate)) {
      const htmlCandidate = `${candidate}.html`;
      try {
        if ((await stat(htmlCandidate)).isFile()) return htmlCandidate;
      } catch {
        return null;
      }
    }
    return null;
  }
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url ?? "/", `http://${host}:${port}`);
    const file = await resolveFile(url.pathname);
    if (!file) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }

    response.writeHead(200, {
      "cache-control": "no-store",
      "content-type": contentTypes[extname(file)] ?? "application/octet-stream",
    });
    createReadStream(file).pipe(response);
  } catch {
    response.writeHead(400, { "content-type": "text/plain; charset=utf-8" });
    response.end("Bad request");
  }
});

server.listen(port, host, () => {
  process.stdout.write(`Static dashboard available at http://${host}:${port}\n`);
});
