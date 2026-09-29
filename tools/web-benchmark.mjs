// Roda a pagina web/ num Chromium headless (Playwright) com imagens do dataset/ e
// salva o CSV do botao "Baixar CSV": o mesmo que uma pessoa faria no navegador,
// mas repetivel no PC e no GitHub Actions.
//
//   npm install && npx playwright install chromium
//   node tools/web-benchmark.mjs --count 200 --out results/benchmark-web.csv
import { createServer } from "node:http";
import { readdir, readFile } from "node:fs/promises";
import { extname, join, resolve, sep } from "node:path";
import { parseArgs } from "node:util";
import { chromium } from "playwright";

const root = resolve(import.meta.dirname, "..");
const { values: args } = parseArgs({
  options: {
    dataset: { type: "string", default: join(root, "dataset") },
    count: { type: "string", default: "0" },
    out: { type: "string", default: join(root, "results", "benchmark-web.csv") },
    timeout: { type: "string", default: "60" },
  },
});

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png" };
const webDir = join(root, "web");

// Servidor estatico minimo: Web Workers com import de modulo nao funcionam em file://.
function serve() {
  const server = createServer(async (req, res) => {
    const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const file = resolve(webDir, `.${path.endsWith("/") ? `${path}index.html` : path}`);
    if (file !== webDir && !file.startsWith(webDir + sep)) { res.writeHead(403).end(); return; }
    try {
      const body = await readFile(file);
      res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" }).end(body);
    } catch { res.writeHead(404).end(); }
  });
  return new Promise(ok => server.listen(0, "127.0.0.1", () => ok(server)));
}

const count = Number(args.count);
const names = (await readdir(args.dataset)).filter(name => name.toLowerCase().endsWith(".jpg")).sort();
const files = (count > 0 ? names.slice(0, count) : names).map(name => join(args.dataset, name));
if (!files.length) throw new Error(`Nenhuma imagem .jpg em ${args.dataset}`);

const server = await serve();
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ acceptDownloads: true });
  page.on("pageerror", error => console.error("Erro na pagina:", error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  const cores = await page.evaluate(() => navigator.hardwareConcurrency);
  console.log(`${files.length} imagens, navegador com ${cores} nucleos logicos. Processando...`);

  await page.setInputFiles("#images", files);
  const started = Date.now();
  await page.click("#run");
  // Termina quando o painel de resultados aparece ou a pagina mostra um erro.
  await page.waitForFunction(
    () => !document.getElementById("results").hidden || document.getElementById("status").classList.contains("error"),
    null,
    { timeout: Number(args.timeout) * 60_000, polling: 1000 },
  );
  const status = await page.textContent("#status");
  if (await page.$eval("#status", el => el.classList.contains("error"))) throw new Error(`A pagina falhou: ${status}`);
  console.log(`${status} (${((Date.now() - started) / 1000).toFixed(1)} s no total, com as 3 rodadas)`);

  const [download] = await Promise.all([page.waitForEvent("download"), page.click("#export-csv")]);
  await download.saveAs(args.out);
  console.log(`CSV salvo em ${args.out}`);
  console.log(await readFile(args.out, "utf8"));
} finally {
  await browser.close();
  server.close();
}
