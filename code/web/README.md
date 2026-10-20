# code/web/ — navegador + Web Workers

Versão publicada no [GitHub Pages](https://lianeheidemann.github.io/parallel-image-pipeline/). Roda o mesmo
pipeline em JavaScript, sem enviar nem salvar imagens: thread principal × 2, 4 e 8 Web Workers.

| Arquivo | Papel |
|---|---|
| `index.html`, `assets/style.css` | Página |
| `assets/app.js` | Entrada: leitura das imagens e botões |
| `assets/runner.js` | Medição: sequencial e fila de imagens para os workers (uma imagem por worker) |
| `assets/worker.js` | Web Worker: processa uma imagem inteira |
| `assets/pipeline.js` | As 6 etapas medidas por imagem: ler o JPG, cinza → blur → Sobel → magnitude, gerar o PNG |
| `assets/processor.js` | Cinza → blur → Sobel → magnitude (espelha `code/local/image_processor.py`) |
| `assets/render.js`, `explain.js`, `format.js` | Resultados, explicações e formatação |
| `assets/report.js` | Linhas do CSV no formato de `output/results/benchmark.csv` (Amdahl igual ao Python) |
| `assets/export.js` | Botão "Baixar CSV" (`benchmark-web.csv`, mesmo formato lido por `code/analysis/`) |

Servir localmente (da raiz do repositório): `npx http-server code/web`. Ao mudar um arquivo, suba o `?v=` de todos
(o teste `tests/web/cache-version.test.mjs` exige o mesmo valor). O deploy é feito por
`.github/workflows/pages.yml` a cada push na `main` que altere `code/web/`.
