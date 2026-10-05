import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../dist/', import.meta.url));
const argument = process.argv.indexOf('--port');
const port = argument >= 0 ? Number(process.argv[argument + 1]) : 8078;
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Port must be from 1024 to 65535.');
await stat(resolve(root, 'index.html')).catch(() => { throw new Error('Build the app first: npm run build'); });
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff': 'font/woff', '.woff2': 'font/woff2' };
const server = createServer(async (request, response) => {
  if (!['GET', 'HEAD'].includes(request.method ?? '')) { response.writeHead(405); response.end(); return; }
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
    let path = resolve(root, `.${pathname === '/' ? '/index.html' : pathname}`);
    if (!path.startsWith(root.endsWith(sep) ? root : root + sep)) { response.writeHead(403); response.end(); return; }
    const info = await stat(path).catch(() => null);
    if (!info?.isFile()) {
      if (extname(pathname)) { response.writeHead(404); response.end(); return; }
      path = resolve(root, 'index.html');
    }
    const data = await readFile(path);
    response.writeHead(200, { 'Content-Type': mime[extname(path)] ?? 'application/octet-stream', 'Cache-Control': 'no-cache', 'X-Content-Type-Options': 'nosniff' });
    response.end(request.method === 'HEAD' ? undefined : data);
  } catch { response.writeHead(400); response.end('Invalid request.'); }
});
server.listen(port, '127.0.0.1', () => process.stdout.write(`Data Orchestration Lab: http://127.0.0.1:${port}\n`));
