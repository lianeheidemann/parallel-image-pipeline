// Etapas 02 a 05 (processPixels): cinza, blur, Sobel e magnitude, como no Python.
import { test } from "node:test";
import assert from "node:assert/strict";
import { processPixels } from "../../code/web/assets/processor.js";

function image(width, height, color) {
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const [r, g, b] = color(x, y), i = (y * width + x) * 4;
    rgba.set([r, g, b, 255], i);
  }
  return rgba;
}

test("imagem uniforme nao tem bordas", () => {
  const edges = processPixels(image(9, 7, () => [120, 60, 200]), 9, 7);
  assert.equal(edges.length, 63);
  assert.ok(edges.every(v => v === 0));
});

test("borda vertical: so as colunas da transicao tem magnitude", () => {
  const width = 12, height = 6;
  const edges = processPixels(image(width, height, x => (x < 6 ? [0, 0, 0] : [255, 255, 255])), width, height);
  for (let y = 0; y < height; y++) {
    const row = Array.from(edges.slice(y * width, (y + 1) * width));
    assert.deepEqual(row.slice(0, 3), [0, 0, 0]);
    assert.deepEqual(row.slice(-3), [0, 0, 0]);
    assert.equal(row[5], 255);
    assert.equal(row[6], 255);
  }
});

test("deterministico, inclusive em imagens de 1 e 2 pixels", () => {
  for (const [w, h] of [[1, 1], [2, 2], [17, 13]]) {
    const rgba = image(w, h, (x, y) => [x * 13 % 256, y * 29 % 256, (x + y) * 7 % 256]);
    assert.deepEqual(processPixels(rgba, w, h), processPixels(rgba, w, h));
  }
});
