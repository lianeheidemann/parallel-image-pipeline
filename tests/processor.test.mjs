// Garante a propriedade central da pagina web: processar a imagem em faixas
// (como os Web Workers fazem) da exatamente o mesmo resultado que processar
// a imagem inteira de uma vez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { processPixels, processRows } from "../docs/assets/processor.js";
import { stripSlice, stripTasks } from "../docs/assets/runner.js";

function randomImage(width, height, seed) {
  const rgba = new Uint8ClampedArray(width * height * 4);
  let state = seed;
  for (let i = 0; i < rgba.length; i++) {
    state = (state * 1103515245 + 12345) >>> 0;
    rgba[i] = state >>> 24;
  }
  return rgba;
}

// Mesmo corte que runParallel (docs/assets/runner.js) envia aos Web Workers.
function processInStrips(img, parts) {
  const out = new Uint8ClampedArray(img.width * img.height);
  for (const task of stripTasks([img], parts)) {
    const { sliceStart, rgba } = stripSlice(img, task);
    out.set(processRows(rgba, img.width, img.height, sliceStart, task.outStart, task.outEnd), task.outStart * img.width);
  }
  return out;
}

for (const [width, height] of [[1, 1], [2, 2], [3, 7], [17, 13], [64, 40]]) {
  for (const parts of [2, 4, 8]) {
    test(`${width}x${height} em ${parts} faixas == imagem inteira`, () => {
      const rgba = randomImage(width, height, width * 31 + height);
      const whole = processPixels(rgba, width, height);
      const strips = processInStrips({ width, height, rgba }, parts);
      assert.deepEqual(strips, whole);
    });
  }
}
