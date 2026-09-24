# web/ — navegador + Web Workers

Versão publicada no [GitHub Pages](https://lianeheidemann.github.io/parallel-image-pipeline/). Roda o mesmo
pipeline em JavaScript, sem enviar nem salvar imagens: thread principal × 2, 4 e 8 Web Workers.

| Arquivo | Papel |
|---|---|
| `index.html`, `assets/style.css` | Página |
| `assets/app.js` | Entrada: leitura das imagens e botões |
| `assets/runner.js` | Medição: sequencial e fila de faixas para os workers |
| `assets/worker.js` | Web Worker: processa uma faixa |
| `assets/processor.js` | Cinza → blur → Sobel (espelha `local/image_processor.py`) |
| `assets/render.js`, `explain.js`, `format.js` | Resultados, explicações e formatação |

Servir localmente: `npx http-server web`. Ao mudar um arquivo, suba o `?v=` de todos
(o teste `tests/web/cache-version.test.mjs` exige o mesmo valor). O deploy é feito por
`.github/workflows/pages.yml` a cada push na `main` que altere `web/`.
