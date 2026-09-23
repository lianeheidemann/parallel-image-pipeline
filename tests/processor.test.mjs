// Garante a propriedade central da pagina web: processar a imagem em faixas
// (como os Web Workers fazem) da exatamente o mesmo resultado que processar
// a imagem inteira de uma vez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { processPixels, processRows, HALO } from "../docs/assets/processor.js";

function randomImage(width, height, seed) {
  const rgba = new Uint8ClampedArray(width * height * 4);
  let state = seed;
  for (let i = 0; i < rgba.length; i++) {
    state = (state * 1103515245 + 12345) >>> 0;
    rgba[i] = state >>> 24;
  }
  return rgba;
}

// Mesmo corte usado por stripTasks/dispatch em docs/assets/app.js.
function processInStrips(rgba, width, height, parts) {
  const out = new Uint8ClampedArray(width * height);
  for (let p = 0; p < parts; p++) {
    const outStart = Math.floor((p * height) / parts), outEnd = Math.floor(((p + 1) * height) / parts);
    const sliceStart = Math.max(0, outStart - HALO), sliceEnd = Math.min(height, outEnd + HALO);
    const slice = rgba.slice(sliceStart * width * 4, sliceEnd * width * 4);
    out.set(processRows(slice, width, height, sliceStart, outStart, outEnd), outStart * width);
  }
  return out;
}

for (const [width, height] of [[1, 1], [2, 2], [3, 7], [17, 13], [64, 40]]) {
  for (const parts of [2, 4, 8]) {
    test(`${width}x${height} em ${parts} faixas == imagem inteira`, () => {
      const rgba = randomImage(width, height, width * 31 + height);
      const whole = processPixels(rgba, width, height);
      const strips = processInStrips(rgba, width, height, Math.min(parts, height));
      assert.deepEqual(strips, whole);
    });
  }
}
