// A pagina usa "?v=..." para o navegador nao reaproveitar arquivos antigos do cache.
// Se um import ficar sem versao ou com versao diferente, um modulo antigo pode ser
// misturado com os novos depois de um deploy.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const web = new URL("../../web/", import.meta.url);
const files = ["index.html", ...readdirSync(new URL("assets/", web)).filter(f => f.endsWith(".js")).map(f => `assets/${f}`)];
const sources = files.map(file => [file, readFileSync(new URL(file, web), "utf8")]);

test("todos os ?v= de web/ tem o mesmo valor", () => {
  const versions = new Set(sources.flatMap(([, text]) => [...text.matchAll(/\?v=([\w.-]+)/g)].map(m => m[1])));
  assert.equal(versions.size, 1, `versoes encontradas: ${[...versions].join(", ")}`);
});

test("todo import local de assets/*.js tem ?v=", () => {
  for (const [file, text] of sources.filter(([file]) => file.endsWith(".js"))) {
    for (const [, spec] of text.matchAll(/(?:from|new URL\()\s*"(\.\/[^"]+)"/g)) {
      assert.match(spec, /\?v=/, `${file}: "${spec}" sem ?v=`);
    }
  }
});
